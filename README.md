# Parsek

[![PyPI version](https://badge.fury.io/py/parsek.svg)](https://badge.fury.io/py/parsek)
[![License](https://img.shields.io/pypi/l/parsek.svg)](https://opensource.org/license/mit/)
[![Python versions](https://img.shields.io/pypi/pyversions/parsek.svg)](https://pypi.org/project/parsek/)

Parsek is a lightweight, pure-Python parser library packaged as a single source file with zero dependencies. It bridges the gap between regular expressions and heavyweight parser generators. Parsek is ideally suited for domain-specific languages (DSLs and mini DSLs), custom data formats, and plugin systems. Grammar rules are defined directly in Python using composable parsing expressions. Parsek supports both combinator-style and finite state machine (FSM) parsers, and both styles can be mixed seamlessly.

- Minimal footprint: single file, zero deps, (optional [minified build](#minified-build))
- Declarative concise grammar in plain Python: no separate grammar file
- Seamlessly blend combinators with FSMs
- Lookahead, lookbehind, backtracking, branching (if_/elif_/else_/endif)
- Versatile accumulation/emission at every step
- Flexible error handling and reporting
- Optional tracing for step-by-step debugging
- Extensively tested ![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)

## Installation

- From PyPI:
  - `pip install parsek`
- Or simply copy `src/parsek.py` into your project.

## Quick start

The parser leverages functional programming techniques, allowing you to easily define complex recursive grammars directly with Python expressions. For example, this complete [JSON parser](#json-parser) uses just a few lines of code:

```python
from parsek import Parser, Val

def parse_json(s: str):
    p = Parser(s)  # create parser instance with input string

    @p.subroutine # JSON value
    def j_val(p: Parser, out, **_kwargs):
        return (p.ws. # skip whitespace
                if_.one({'null': None, 'true': True, 'false': False}, out).
                elif_.one(p.decimal, out).
                elif_.one(p.string, out, quotes={'"':'"'}). # JSON strings are double-quoted only
                elif_.one(p.collection, j_val, l := []).do(p.accumulate, out, l). # array [...]
                else_.one(p.collection, j_kv, d := {}, brackets={'{': '}'}).do(p.accumulate, out, d). # object {...}
                endif)

    @p.subroutine # key:value pair in JSON object
    def j_kv(p: Parser, out, **_kwargs):
        return p.one(p.string, k := p.Val(), quotes={'"':'"'}).ws.one(':').ws.one(j_val, (out, k))

    r = Val() # resulting JSON goes here
    p.ws.one(j_val, r, nomatch='Invalid JSON').ws.one(p.EOF, nomatch='Unexpected trailing input')
    return r.value
```
 For this example and more ([CSV](#csv-parser), [mini DSL](#mini-dsl-parser), [INI/config](#iniconfig-parser)), see the [Examples](#examples) section below.

## Table of Contents
- [Guide](#guide)
  - [Matching](#matching)
  - [Quantifiers](#quantifiers)
  - [Accumulation & Emission](#accumulation--emission)
  - [Lookahead, Backtracking, & Flow Control](#lookahead-backtracking--flow-control)
  - [Debugging & tracing](#debugging--tracing)
  - [Performance and general tips](#performance-and-general-tips)
- [Quick reference](#quick-reference)
- [Minified Build](#minified-build)
- [Examples](#examples)

## Guide

### Matching
Matching input is done with **matchers** - literals, predicates, subroutines or combinations thereof. Matchers are passed to **quantifiers**, which perform the actual parsing and accumulation. The simplest quantifier is `one(matcher, ...)`, which matches exactly one occurrence of the matcher at the current input position. On success, the parser advances by the match length (**consuming** input) and returns success (self). On failure, the position remains unchanged (for simple matchers) or advanced to the failure point (for complex ones like subroutines), returning failure (falsy). All other quantifiers (`zero_or_more`, `one_or_more`, etc.) are built on top of `one()` and accept the same arguments.
```python
from parsek import Parser, In, Not

p = Parser("hello,  World!")  # instantiate parser with input string

# match 'hello', one or more non-alpha/non-space chars, 'world' (ignoring case), and '!'
p.one('hello').one_or_more(Not(str.isalpha, str.isspace)).one(str.isalpha, ic=True).one(In('!?.'))
assert p.one(p.EOF) # ensure we consumed all input
```
The core feature of Parsek is support for **chain expressions**. All quantifiers and flow-control operations return the current `Parser` instance (on success) or special opaque object (derived from `Parser.Branch` or `Parser.Stop`) that directs further execution of the chain. This allows chaining multiple quantifiers and flow control operations in a single expression. In the example above, if `one('hello')` fails, the entire expression short-circuits and returns Parser.Fail (a falsy object with `is_ok=False`). Similarly, if any subsequent quantifier fails, the whole chain fails. With flow-control elements like `if_`, `else_`, `endif`, `fail`,  and side effects like `do`, chain expressions enable compact and expressive encoding of parsing logic.

### Matchers
A matcher is anything accepted by `p.one(...)` (or any other quantifier) as first positional argument. Supported kinds:

- Literals
  - `'a'`, `'hello'` - string literals
  - `Parser.EOF` or `Parser.END_CHAR` - the implicit end-of-input sentinel (also a string)
- Character sets and predicates
  - Unary predicate on a single char: `str.isdigit`, `str.isalpha`, custom `lambda ch: ...`
    - for case-insensitive matching (`ic=True`), the passed char is already lower-cased.
  - Non-unary predicate on a single char: lambda ch, arg1, ...: ...
    - additional args are passed by the quantifier, e.g. `p.one(lambda ch, s: ch in s, 'abc')`
    - for case-insensitive matching (`ic=True`), the predicate receives the `ic=True` kwarg, and lower-cased `ch`.
  - `In('abc')` tests membership, `ch in 'abc'`
  - `p.chars('^_a-zA-Z0-9$')` character-class matcher supporting ranges, negation (^), escapes (\), and `$` (the `END_CHAR` sentinel)
- Mapping
  - Dict key match (literal or `Val`) that emits a mapped value into accumulators:
    - `{'true': True, 'false': False}`
- Subroutines
  - Functions decorated with `@parser_subroutine` (aliases: `@Parser.subroutine`, `@Parser.sr`) - may be recursive (as grammar rules often are). Subroutines receive the current `Parser` instance as first arg, followed by any positional and keyword args passed by the quantifier. They must return truthy (success) or falsy (failure). Typically if you need to match more than a character/literal as a subpattern, you use a subroutine.
  - New-stack variant: `@parser_subroutine_new_stack` for FSM-style routines that should not mutate the caller’s state. Creates a new parser instance for the subroutine; only the position is merged back on return.
  - Case-insensitive kwarg (`ic=True`) if present is simply passed down to the subroutine (input is not modified).
- Alternation
  - Tuple of matchers: `('a', 'b', str.isdigit)` - the first that matches wins. Any of the above matcher kinds can be used inside the tuple.
  - Tuple/list/set of literals or `Val` objects: `('a', 'b', 'hello')` - the first that matches wins.
- Case-insensitive matching (ignore case, IC)
  - Any matcher above with `ic=True` argument in any quantifier: `p.one('world', ic=True)`
  - OR with quantifier name suffix `_ic`/`i`, e.g., `p.one_ic('world')` (see Quantifiers). This is just a shorthand for `ic=True` and results in the same behavior.
  - For subroutine matchers and non-unary predicates, `ic=True` is also passed down to the matcher.
- Negation
  - `Not(matcher1, matcher2, ...)` negates any matcher or alternation tuple of matchers. If any matcher matches, `Not` fails; if all matchers fail, `Not` matches (consuming single char). `Not` is treated specially by the parser for efficiency and correctness.

Examples:
```python
from parsek import Parser, Val, In

p = Parser(input_string)
p.one('a')             # match 'a'
p.one(str.islower)     # match any lowercase letter
p.one(In('XYZ'))       # match any of 'X', 'Y', or 'Z'
p.one(('X', 'Y', 'Z')) # same as above, alternation tuple
p.one(p.chars('XYZ'))  # same as above, char set matcher
p.one(p.chars('X-Z'))  # same as above, char class matcher
p.one({'X': 1, 'Y': 2, 'Z': 3}, v := Val())  # match and emit mapped value into v
p.one(lambda ch: ch in 'XYZ')  # match any of 'X', 'Y', or 'Z' using a custom predicate
p.one(lambda ch, s: ch in s, 'XYZ')  # same as above, non-unary predicate with extra arg

@p.subroutine  # subroutine matcher
def token(p): # identifier type token: [a-zA-Z_][a-zA-Z0-9_]*
    return p.one((str.isalpha, '_')).one_or_more(lambda ch: ch.isalnum() or ch == '_')

p.one(token)  # match an identifier token as defined above

# Case-insensitive matchers:
p.one('a', ic=True)  # match 'a' or 'A'
p.one_ic('a')        # same as above, shorthand with _ic suffix
p.one(p.chars('a-z'), ic=True)  # match any letter a-z or A-Z

# Negation:
p.one(Not(str.isalpha))  # match any non-alpha char
p.one(Not(' ', '\t', '\r', '\n'))  # match any non-whitespace char
```

### Quantifiers

Quantifiers control repetition and optionality. All accept the same matcher kinds and arguments as `one(...)`. And in fact, all other quantifiers are implemented on top of `one(...)`. All quantifiers can also accumulate matched text or emitted values into various kinds of **sinks** (see [Accumulation & Emission](#accumulation--emission) below). Supported quantifiers:

- Core
  - `one(m, ...)` - exactly one
  - `zero_or_one(f, ...)` - optional one
  - `one_or_more(f, ...)` - at least one (greedy)
  - `zero_or_more(f, ...)` - optional, multiple (greedy)
  - `repeat(min, max, f, ...)` - at least `min`, at most `max` (both inclusive)
    - and its aliases: `exactly(n, f, ...)`, `at_least(n, f, ...)`, `at_most(n, f, ...)`
  - Case-insensitive: add `ic=True` argument to any quantifier, or use `_ic` suffix on quantifier name, e.g. `one_ic`, `repeat_ic`, etc.
    - the `_ic` suffix is just a shorthand and results in the underlying quantifier being called with `ic=True`.
  - `nomatch='message'` kwarg on any quantifier raises (or invokes your handler) when no match occurs.
- Short aliases
  - `x1   == one`
  - `x1_  == one_or_more`
  - `x0_  == zero_or_more`
  - `x0_1 == zero_or_one`
  - `xM_N == repeat(M, N, ...)` (dynamic, generated on demand)
- Dynamic quantifiers (generated on demand)
  - Exact: `x2(f, ...)` - exactly 2
  - Ranges: `x2_5(f, ...)` - 2 to 5
  - _"Or more"_: `x2_(f, ...)` - 2 or more
  - Case-insensitive: suffix `i`, e.g. `x2i`, `x2_5i`, `x2_i`
- Spelled-out variants (generated on demand)
  - `two(f, ...)`, `three(f, ...)`, …
  - `two_to_five(f, ...)` or `two_to_5(f, ...)`
  - `four_or_more(f, ...)`
  - Case-insensitive: `_ic` suffix, e.g. `two_ic`, `two_to_five_ic`

All quantifiers share the same call signature as `one(...)`:
```python
def one(self, matcher, *args, *, acc=None, ic=False, nomatch=None, **kwargs)
```
>➰ *Note:* `acc`, `ic`, and `nomatch` are keyword-only arguments and don't actually appear in the formal signature of `one(...)` or any other quantifier - they're shown here for clarity.
- `matcher` - any matcher as described above
- `*args`, `**kwargs` - forwarded to the underlying `one()` call (repeatedly, by all quantifiers other than `one`):
  - For non-unary predicates or subroutines, these are passed directly to the matcher.
    - For subroutines, the current `Parser` instance is automatically passed as the first argument (don't add it yourself).
  - For other matchers, these args/kwargs act as accumulator targets.
- `acc` - explicit accumulator (sink) for the entire quantifier call. Unlike positional accumulator args, it's used once per quantifier call. Can be one or more accumulators. See [Accumulation & Emission](#accumulation--emission) for details.
- `ic` - if True, enables case-insensitive matching for any matcher that supports it. For subroutines and non-unary predicates, `ic=True` is also passed down to the matcher. Avoid writing `ic=False` (default) as it just clutters the call sites, and must then be added to your subroutine signatures.
- `nomatch` - if given (string or callable), raises a `ValueError` (or calls your error handler) when no match occurs.

Examples:
```python
from parsek import Parser, Val

p = Parser("aa123bbbXYZ")

# exactly two 'a'
p.exactly(2, 'a', lambda v: print(f"Got {v}")) # lambda is an accumulator; called twice
# -> prints "Got a" twice

# exactly three digits
p.three(str.isdigit, acc=lambda v: print(f"Got {v}")) # lambda is an accumulator; called once
# -> prints "Got 123" once

# 1..3 'b' into a list
bl = []
p.at_most(3, 'b', bl) # bl is an accumulator
assert bl == ['b', 'b', 'b']

# 3 uppercase letters using a dynamic quantifier
up = Val()
p.x3(str.isupper, up)  # up will accumulate the 3 uppercase letters
assert up.value == 'XYZ'
```
Note that you can simply use Python's `while` loop for any repetition you like. This is a valid and useful technique.
```python
p = Parser("aaaaab")
while p.one('a'):
    print('a')
```
While example above is obviously contrived, as zero_or_more('a') would not only be shorter but also faster ([`while` can be just as fast](#get-one-ctx)), there are cases where using `while` is perfectly fine like in the [INI/config parser example](#iniconfig-parser).


### Accumulation & Emission

Accumulation/emitting of parsed text can be accomplished in various ways:
- All quantifiers can collect matched text into “sinks” as described in [Quantifiers](#quantifiers):
  - Pass sinks either as `acc=...` or as extra positional args (when the matcher does not consume those args).
  - Supported sinks:
    - `Val` - flexible (variant/union) scalar accumulator (str/int/float/bool); has many convenience features that mesh well with Parser API paradigm.
    - `list`, `set` - via `append`/`add`
    - Mapping sink: `(dict, key, [converter_or_combiner])`
    - Callable sink: `sink(value)`
    - Multiple targets of the above: `Acc(a, b, ...)` or tuple with first element a `Val`: `(val_a, list_b, ...)`. `Acc` is mostly to disambiguate from a mapping tuple sink.
    - `Parser.accumulate(out, v)` describes the full contract, and can be used as a convenient emitter in chain expressions (with `do()`).
- `do()\do_if()` - at any point in the parsing tree, call any callable with `do(func, *args, **kwargs)` (or predicated `do_if`) to invoke a custom side-effect function with any args/kwargs you want: `do(print, "Matched", value)`, `do(l.append, value)`, or `do(lambda: my_emit(value))`, etc.
- `p.save_pos('tag')` and `copy('tag', sink)` - save current position with `save_pos` at any point, and later copy the input slice from that position to current position into any sink with `copy('tag', sink)`. This is rarely needed but can be useful in some cases.

Examples:
```python
from parsek import Parser, Val, In

p = Parser("hello abc 123 xyz 456 world")

p.save_pos('hi') # save start position

# Val as string accumulator
a = Val()
p.one_or_more(str.isalpha, a).ws
assert a == 'hello' and a.value == 'hello'

# Mapping sink -> modifies dictionary
d = {}
p.one_or_more_ic(str.isalpha, acc=(d, 'word')).ws
# NOTE: we are using acc= here ⤴︎ to call the mapping sink only once for the whole match
assert d == {'word': 'abc'}

# list as accumulator
n = []
p.one_or_more(str.isdigit, n).ws
assert n == ['1', '2', '3']

# lambda as accumulator
p.one_or_more(In('xyz'), lambda v: print(f"Got {v}")).ws
# -> prints "Got x", "Got y", "Got z"

# accumulating with acc= vs. positional args
l = []      # l will be passed to underlying one() calls, so it will get called 3 times
s = Val()   # acc=s will be called once by the at_most for the whole match
p.at_most(3, str.isdigit, l, acc=s).ws
assert l == ['4', '5', '6']
assert s == '456'

# do() to call any function at any point
p.one('world').do(print, "Matched world").do(l.append, 'world')
assert l == ['4', '5', '6', 'world']

# use copy to capture input slice from our saved 'hi' position to current position
all = Val()
p.copy('hi', all)
assert all == 'hello abc 123 xyz 456 world'
```

### Error handling
There are a few ways to handle parsing errors:
- Use `nomatch='message'` argument on any quantifier to raise a `ValueError` when no match occurs. The raised error includes the message, current position, and a snippet of the input around the error position.
- Use `nomatch=callable` to call your custom error handler instead of raising. The callable receives the `Parser` instance, from which you can get the current position, input snippet, etc.
- call `err()` or `err_if()` anywhere in the parsing tree to raise an error (or call your handler) and halt the parser immediately.
- finally just use `do()` to call any function at any point, including raising your own exceptions.

```python
p = Parser("42x")
r = Val()
# require at least one digit
p.one_or_more(str.isdigit, r, nomatch="Expected at least one digit")

# Custom error handler example:
class MyError:
    def __init__(self, msg):
        self.msg = msg
    def __call__(self, p: Parser):
        snippet = p.source[max(0, p.pos-5):p.pos+5]
        raise ValueError(f"MyError: {self.msg} at pos {p.pos}: ...{snippet}...")

# require exact suffix 'kg' and less than 100kg
p.one('kg', nomatch=MyError("Expected 'kg'")).err_if(lambda: r.value >= 100, MyError("Weight too large"))
```

[↑ Back to top](#table-of-contents)

## Lookahead, Backtracking, & Flow Control

Parsek supports speculative parsing with lookahead/commit/backtrack, and branching constructs. Think of them as parser equivalents of `if` / `elif` / `else` in Python code. There are also lookbehind (`behind`) and `peek` operations that do not consume input.

### Core Operations
- `lookahead` (*alias:* `if_`):
    Push current position on the backtrack stack. Must be followed by commit, backtrack, or alt.
- `commit` (*alias:* `endif`):
    Pop backtrack stack and commit to the current position.
- `backtrack()`:
    Pop backtrack stack and restore previous position. Note that this is a method and not a property like the others.
    This is a reminder **NOT** to call it inside chain expressions (use `alt` instead).
- `alt` (*alias:* `else_`):
    Create an alternative branch in a chain expression. One alt allowed per lookahead. Automatically commits or backtracks.
    You can have as many nested lookahead/alt/merge inside an alt branch as needed.
- `merge` (*alias:* `endif`):
    Merge an alt branch back into the main flow.
- `elif_`:
    is its own construct that allows multiple branches in an if_ chain expression in lieu of nesting lookaheads/alt/merge.
- `fail`, `fail_if` - fail the current branch early, skips to the next else_/elif_/alt or endif_/merge. Don't confuse with `err` which raises an error and halts the parser, `fail` is like a silent backtrack.
- `break_`, `continue_`, `back`, `back_ok` - these stop the whole chain expression immediately either committing (break_, continue) or backtracking (back, back_ok) and returning success (continue, back_ok) or failure (break_, back). While invaluable, use these sparingly as they can make the parsing logic harder to follow.
- `end` - immediately puts the parser in end state, stopping all further parsing, returns success. Parser.is_active will be False after this and Parser.is_end_state will be True.
- `err`, `err_if` - raise an error (or call your error handler) and halt the parser immediately. Don't confuse with `fail`/`fail_if` which simply fails the current branch and backtracks silently.
- `behind(matcher, ...)` - lookbehind: match the given matcher just before the current position without consuming input. The scan is backwards from current position. Fails if the matcher fails. Arguments are the same as for `one()`.
- `peek(matcher, ...)` - peek ahead: match the given matcher at current position without consuming input. The scan is forwards from current position. Fails if the matcher fails. Arguments are the same as for `one()`.

#### Guidelines

- Every `lookahead` must be matched by `commit`/`backtrack` or `alt`/`merge`.
- In chain expressions use `if_/elif_/else_/endif` especially for multiple branches, as `elif_` has no direct equivalent in lookahead/alt/commit and makes multiple branches much cleaner and easier to read.
- `if_`/`else_`/`endif` are **literal aliases** for `lookahead`/`alt`/`merge` and can be used interchangeably.
- Use `fail`/`fail_if` to backtrack silently; `err` or `err_if` to halt with error.

#### Simple branching:

A simple lookahead/consume or backtrack, note how tedious it is, we will see how chain expressions streamline this greatly:
```python
p = Parser("abc")
if p.lookahead.one('a').ws.one('b'): # match a and b separated by optional whitespace
    p.commit()  # consume 'a'
    print("Found a & b")
else:
    p.backtrack()  # restore position
    print("No a & b")
```
Now the same with chain expressions:
```python
p.lookahead.one('a').ws.one('b').do(print, "Found a & b").alt.do(print, "No a & b").merge
# same but using the if_/else_ aliases:
p.if_.one('a').ws.one('b').do(print, "Found a & b").else_.do(print, "No a & b").endif
```
Note, not only `if_/else_` reads better but also allows multiple branches with `elif_` without nesting:
```python
( p.if_.one('a').ws.one('b').do(print, "Found a & b").
    elif_.one('b').do(print, "Found just b").
    elif_.one('c').do(print, "Found c").
    else_.do(print, "No a, b, or c").
    endif )
# same as using nested lookahead/alt/merge:
( p.lookahead.one('a').ws.one('b').do(print, "Found a & b").
    alt.lookahead.one('b').do(print, "Found just b").
        alt.lookahead.one('c').do(print, "Found c").
            alt.do(print, "No a, b, or c").
            merge.   # matching all the merges with
        merge.       # the corresponding lookaheads
    merge )          # gets tedious quickly!
```
Of course each branch can have as many quantifiers and flow control elements as needed, not just a single `one(...)` like in the examples above.

#### Semantics, failure, and peeking

Since `if_ ... endif` is a lookahead it never fails as a whole even if it backtracks (that's the entire point of a lookahead). However, the `else_` branch is *not* a lookahead and when it fails, the entire if-elif-else chain fails. Note, `elif_`, just like `if_`, is a lookahead so it behaves the same: doesn't fail just backtracks. You can explicitly fail any branch by calling `fail`.
Consider this example:
```python
p = Parser("hello planet")
ok = p.one('hello').ws.one('world').is_ok
assert not ok and p.pos == 6 # match failed and parser advanced to after 'hello '
p.pos = 0  # reset Parser's position

ok = p.if_.one('hello').ws.one('world').endif.is_ok
assert ok and p.pos == 0  # match OK and parser backtracked to start

ok = p.if_.one('hello').ws.one('world').else_.fail.endif.is_ok
assert not ok and p.pos == 0  # match FAILED and parser backtracked to start

# Now with a successful match:
p = Parser("hello world")
ok = p.one('hello').ws.one('world').is_ok
assert ok and p.pos == 11 # match OK and parser advanced to after 'world' (END_CHAR)
p.pos = 0  # reset Parser's position

ok = p.if_.one('hello').ws.one('world').endif.is_ok
assert ok and p.pos == 11  # match OK and parser parser advanced to after 'world' (END_CHAR)
p.pos = 0  # reset Parser's position

# fail inside if_ branch forces backtrack even though the branch would have succeeded:
ok = p.if_.one('hello').ws.one('world').fail.endif.is_ok
assert ok and p.pos == 0  # match OK and parser backtracked to start
# this could be useful if you want to peek ahead without consuming input.

# Note that there's Parser.peek() for that too but it requires a subroutine:
ok = p.peek(p.sr(lambda p: p.one('hello').ws.one('world'))).is_ok
assert ok and p.pos == 0  # match OK and parser backtracked to start
# if the peek's subroutine fails:
ok = p.peek(p.sr(lambda p: p.one('hello').ws.one('planet'))).is_ok
assert not ok and p.pos == 0  # match FAILED and parser backtracked to start
```

## Debugging & tracing
>⚠️ *Note:*  the source of many infinite loop problems is forgetting to handle the end-of-input sentinel: `END_CHAR`/`EOF`. See here: [handling end-of-input](#end-of-input).

>⚠️ *Note:* All arguments in the chain expression are __always__ evaluated even for the failed portions of the chain. While in most cases this is not an issue, it can be if the argument is only valid in certain branches and can result in subtle bugs. In such cases either use reference types (like `Val`, `list`, etc.) or defer evaluation with a callable (like an inline lambda).

#### Enable tracing (debug builds only):

```python
Parser.set_trace(level=3, color=True, out=print)
```

- Levels: 0–5 (0=off, 5=most verbose)
- Colorized call-sites, inputs, and decisions
- Low overhead when disabled

#### Parser.PARSE_LIMIT
Limit _all_ looping quantifiers with `Parser.PARSE_LIMIT` to catch runaway loops faster:

```python
Parser.PARSE_LIMIT = 100 # default is 100000
```

## Performance and general tips

#### ✅ disable tracing
>Tracing is off by default, but if you enabled it for debugging, turn it off when done. Tracing adds significant overhead: it has to walk the call stack with `inspect`, parse lambda source code, colorize messages, etc. It is heavy! Also running with `-O` eliminates all debug assertions and removes tracing code completely. The [minified build](#minified-build) does all that without needing `-O`.

#### ✅ structure your grammar to minimize backtracking
>This is obvious but worth mentioning. Avoid having long branches that are likely to fail in favor of the following shorter branch that are more likely to succeed.

#### ✅ cache matchers
>Instead of using `one(In('abc'))` or similar, cache the matcher in a local variable and use that:
```python
  m = p.chars('^abc$')  # cache the matcher, even if chars() also caches internally
  p.one(m)              # faster than p.one(p.chars('^abc$'))
```

#### ✅ accumulate with `acc=`
>When accumulating with a quantifier other than `one`, consider using the `acc=` argument instead of passing the accumulator as a positional argument (**if it is appropriate!**). Using `acc=` calls the accumulator only once per quantifier call instead of passing it to the underlying `one` which will call it repeatedly on each match (note that sometimes you might want exactly that!). For example,
```python
  p = Parser("aaaaab")
  s = Val()
  p.one_or_more('a', s)  # calls s.append('a') 5 times!
  p.pos = 0  # reset position
  p.one_or_more('a', acc=s)  # calls s.append('aaaaa') only once!
```
>With `one`, using `acc=` or positional arg for accumulator makes no difference in such cases. Note, the `acc=` still useful when using `one` with a subroutine matcher, as all positional args and kwargs, except `acc=` are passed to the subroutine. So accumulator in `acc=` will get the entire input matched by the subroutine regardless of what the subroutine does/accumulates internally:
```python
  p = Parser("3.14")
  # parse a decimal number into a float and also capture the string representation
  p.one(p.decimal, pi := Val(), acc=(pi_str := Val()))
  assert pi.value == 3.14 and pi_str.value == '3.14'
```

<a id="end-of-input"></a>

#### ✅ handle end-of-input: `END_CHAR` (`EOF`)
>`END_CHAR`/`EOF` is Parsek’s implicit end-of-input sentinel. It simplifies parsing logic by unifying termination handling, but it can also cause infinite loops if ignored. Once the parser reaches the end of input, every subsequent read returns `END_CHAR`/`EOF` — indefinitely. You must therefore handle it explicitly, e.g.:
```python
  p.if_.one(p.EOF).end.endif
```
>This puts the parser in the end state, causing all subsequent quantifiers to return immediately with `Parser.End` (a truthy value).
>A common pitfall involves an overly inclusive `Not(...)` without `END_CHAR` in its test set; it will keep matching at the end of input and never fail, resulting in an infinite loop. If appropriate, include `END_CHAR` in the `Not(...)` test set, to ensure it stops at the end of input:
```python
  m = Not(In('abc' + p.END_CHAR)) # matcher: fails on 'a', 'b', 'c', or END_CHAR
  # or equivalently:
  m = p.chars('^abc$')  # where '$' represents END_CHAR
```
>During initial development you can ignore EOF but set `Parser.PARSE_LIMIT` to a small value (e.g. `20`) to catch potential infinite loops quickly. Once the parser behaves correctly, add proper EOF handling and remove the limit.

<a id="get-one-ctx"></a>

#### ✅ `get_one_ctx()` and `one_with_ctx()`
>Every time you use a quantifier the optimized version of a matcher harness is selected. So looping quantifiers like `one_or_more` first get the optimized harness with `get_one_ctx()` and then use it repeatedly with `one_with_ctx()`. You can do the same. For example:
```python
  p = Parser("aaaaab")
  ctx = p.get_one_ctx('a')  # pre-resolve matcher
  while p.one_with_ctx(ctx):  # slightly faster than calling one('a') repeatedly
      pass
```
>`get_one_ctx()` resolves the type of matcher, whether it's a literal, unary predicate, subroutine, etc., then if it is being negated with `Not(...)`, and finally, if it is case-insensitive (`ic=True`). It then returns a context object that includes an optimized harness function plus context data like if the matcher takes extra args.

#### ✅ `@unary` decorator
>You can mark your custom unary matchers with `@unary` decorator to minimize overhead of checking the matcher type on each `one()` or `get_one_ctx()` call. This also can be used to disambiguate the matcher type. `@unary` decorator simply sets `__arity=1` attribute on the receiver object; and `is_unary()` checks for that attribute first.
```python
  from parsek import Parser, unary

  @unary # <- optional, speeds up matcher dispatch
  def is_vowel(ch):
      return ch in 'aeiou'

  p = Parser("aeiouxyz")
  p.one_or_more(is_vowel, v := [])
  assert v == ['a', 'e', 'i', 'o', 'u']
```


## Examples

### JSON parser
<details open>
<summary>EBNF grammar</summary>

```ebnf
value   = object | array | string | number | "true" | "false" | "null" ;
object  = "{" ws [ member ( ws "," ws member )* ] ws "}" ;
member  = string ws ":" ws value ;
array   = "[" ws [ value ( ws "," ws value )* ] ws "]" ;
string  = '"' chars '"' ;
number  = '-'? int frac? exp? ;
int     = '0' | [1-9] [0-9]* ;
frac    = '.' [0-9]+ ;
exp     = ('e'|'E') ('+'|'-')? [0-9]+ ;
ws      = (space | tab | newline | carriage return)* ;
```

</details>

We use built-in `decimal` and `string` subroutines to parse the corresponding literals. Note that `Parser.decimal` is more permissive than the EBNF number rule above. To handle arrays `[...]` and objects `{...}` we use `collection` with appropriate _item_ subroutines which are recursive. We allow empty items, and trailing commas in arrays and objects, which is not strictly valid JSON but often convenient. You can easily modify the code to disallow both or either empty items or trailing/consecutive commas if needed with `empty_item` argument to `collection`.
```python
from parsek import Parser, Val

def parse_json(s: str):
    p = Parser(s)  # create parser instance with input string

    @p.subroutine # JSON value
    def j_val(p: Parser, out, **_kwargs):
        return (p.ws. # skip whitespace
                if_.one({'null': None, 'true': True, 'false': False}, out).
                elif_.one(p.decimal, out). # p.decimal is more permissive than ebnf's number
                elif_.one(p.string, out, quotes={'"':'"'}). # JSON strings are double-quoted only
                elif_.one(p.collection, j_val, l := []).do(p.accumulate, out, l). # array [...]
                else_.one(p.collection, j_kv, d := {}, brackets={'{': '}'}).do(p.accumulate, out, d). # object {...}
                endif)

    @p.subroutine # key:value pair in JSON object
    def j_kv(p: Parser, out, **_kwargs):
        return p.one(p.string, k := p.Val(), quotes={'"':'"'}).ws.one(':').ws.one(j_val, (out, k))

    r = Val() # resulting JSON goes here
    p.ws.one(j_val, r, nomatch='Invalid JSON').ws.one(p.EOF, nomatch='Unexpected trailing input')
    return r.value
```
-----------------------------------------------------------------
### Mini DSL parser

This parser is similar to the one we use in Parsek's own Parser.chars() method to parse character class specifications like `^a-zA-Z0-9_$`. While the format is simple, it has some challenges like handling the `\` escapes, context-sensitive `^` (negation only at start, literal otherwise), `$` (end-of-input sentinel at the end but literal anywhere else), and `-` dash which either denotes a range (only between two chars that are themselves not ends of a range) or is a literal.

```python
from parsek import Parser, Not, Val

def parse_char_spec(spec: str):
    p = Parser(spec)
    trailing_eof = Val(False) # set to True if $ is present at end

    @p.sr # escaped or plain char, esc flag will be True if escaped
    def char(p, out, esc = None):
        return p.if_.one('\\').one(Not(p.EOF), out, esc).else_.one(p.NOT_EOF, out).endif
        #            NOTE:  Not(p.EOF)⤴︎ is common so there's p.NOT_EOF⤴︎ const for it

    @p.sr # range: 'a-z' → ('a','z') appended to out
    def range_(p, left, out):
        return p.one('-').one(char, e := Val()).do(lambda: out.append((left, e.v)))

    @p.sr # range, char, or trailing '$'
    def atom(p, out):
        return (p.one(char, left := Val(), esc := Val(False)).
                if_.one(range_, left.v, out).
                elif_.fail_if(esc or left != '$').one(p.EOF, lambda _: trailing_eof.set(True)).
                else_.do(out.append, left.v).endif)

    p.zero_or_one('^', neg := Val(False)).zero_or_more(atom, r := [])
    return r, neg.v, trailing_eof.v # -> [('a','z'), 'A'], True, False
```

Here's an alternative implementation of the `atom` subroutine that avoids the extra lookahead branch by relying on the computed `p.ch` property returning the current character. It does the same thing as above but less parsingly:

```python
@p.sr # range, char, or trailing '$'
def atom(p, out):
    return (p.one(char, left := Val(), esc := Val(False)).
            if_.one(range_, left.v, out).
            else_.do(lambda: trailing_eof.set(True) if (p.ch == p.EOF and left == '$' and not esc) else
                             out.append(left.v)).
            endif)
```

-----------------------------------------------------------------

### CSV parser

<details>
<summary>EBNF grammar <i>(click to expand)</i></summary>

```ebnf
csv           = record , { nl , record } , [ nl ] ;
record        = field , { "," , field } ;
field         = quoted_field | bare_field ;
quoted_field  = '"' , { qchar | '""' } , '"' ;
bare_field    = { char - '"' - "," - nl } ;
qchar         = char - '"' ;
char          = ? any Unicode character except newline ? ;
nl            = "\r\n" | "\n" ;
```
</details>

In this CSV parser we don't use any of the built-ins (even though `collection` could be useful) and it's pretty much just a direct encoding of the EBNF grammar above with each rule corresponding to a subroutine.

```python
from parsek import Parser, Val

def parse_csv(s: str):
    p = Parser(s)
    rows = []

    nl = ('\r\n', '\n') # newline matcher

    @p.subroutine # quoted field: '"' { qchar | '""' } '"'
    def quoted_field(p: Parser, out):

        @p.subroutine # Escaped doubled quote "" (=> ") stop on first unescaped non-quote char
        def qcontent(p: Parser, out):
            return p.if_.one('""').do(out.append, '"').else_.x1_(p.chars('^"$'), acc=out).endif

        return p.one('"').x0_(qcontent, txt := Val('')).one('"').do(out.append, txt.value)

    @p.subroutine # Any chars except quote, comma, or newline
    def bare_field(p: Parser, out):
        txt = Val()
        return p.x0_(p.chars('^",\r\n$'), acc=txt).do(out.append, txt.value)

    @p.subroutine # field = quoted_field | bare_field
    def field(p: Parser, out):
        return p.if_.one(quoted_field, out).else_.one(bare_field, out).endif

    @p.subroutine # record = field { "," field }
    def record(p: Parser):
        row = []
        return (p.one(field, row).
                  x0_(p.sr(lambda p: p.one(',').one(field, row))).
                  do_if(lambda: not (len(row) == 1 and row[0] is None), rows.append, row))

    # csv = record { nl record } [ nl ] EOF
    p.one(record, nomatch='Invalid CSV record') \
     .x0_(p.sr(lambda p: p.one(nl).one(record))) \
     .x0_(nl) \
     .one(p.END_CHAR, nomatch='Unexpected trailing input')

    return rows
```
-----------------------------------------------------------------
### INI/Config parser
<details>
<summary>EBNF grammar <i>(click to expand)</i></summary>

```ebnf
ini           = { ws* ( section | key_value | comment | empty_line ) } ;
section       = ws* "[" ws* section_name ws* "]" ws* nl ;
section_name  = 1*( char - "[" - "]" - nl ) ;
key_value     = ws* key ws* "=" ws* value ws* comment? nl ;
key           = { char - "=" - "[" - "]" - "#" - ";" - nl } ;
value         = quoted_string | number | boolean | null | bare_value ;
quoted_string = Parser.string ; (* supports both " " and ' ' quotes, with escapes *)
number        = Parser.decimal ;  (* permissive: allows leading 0, exp, and fractions per Parser.decimal *)
boolean       = "true" | "false" | "on" | "off" | "yes" | "no"  ;  (* case-insensitive *)
null          = "null" | "none" ;  (* case-insensitive *)
bare_value    = { char - "#" - ";" - nl } ;  (* then trimmed *)
comment       = ws* ("#" | ";") { char - nl } nl ;
empty_line    = ws* nl ;
ws            = " " | "\t" ;
nl            = "\r\n" | "\n" ;
char          = ? any Unicode character ? ;
```

</details>

In this parser we use Python's `while` loop to drive the main parsing flow. As we parse each section and key-value pair we emit the results into `cfg` dictionary using the `_enter_section` and `_set_kv` functions, which are called with `do` at the appropriate points in the parsing tree. Note the use of `do_if` in `key_value` where the whole parser branch executes only on some external condition. We introduced the use of aliases for the quantifiers to make the parsing expressions more concise arguably at the cost of some readability. Finally, we added more timely and appropriate error messages with `nomatch` and `err_if`.

```python
from parsek import Parser, In, Val

def parse_ini(s: str):
    p = Parser(s)              # new parser with input string
    cfg: dict[str, dict] = {}  # result goes here
    current_sec = Val(None)    # current section name or None (DEFAULT)

    def _enter_section(name: str):  # emitter: [section]
        current_sec.set(name)       # update current section
        cfg.setdefault(name, {})    # ensure section exists

    def _set_kv(k: str, v):         # emitter: key = value
        sec = current_sec.value or 'DEFAULT' # use DEFAULT section if none specified
        cfg.setdefault(sec, {})    # ensure section exists
        cfg[sec][k] = v            # set key-value in current section

    ws = In(' \t')     # whitespace matcher
    nl = ('\r\n','\n') # newline matcher

    @p.subroutine # a comment or empty line(s)
    def comment_or_empty(p: Parser):
        return (p.zero_or_more(ws). # optional leading spaces
                if_.one(('#', ';')).x0_(p.chars('^\n\r$')).zero_or_more(nl).
                elif_.one_or_more(nl). # empty line(s) ?
                else_.one(p.END_CHAR).end.endif) # if not end-of-input return False

    @p.subroutine # value of a key=value pair
    def value(p: Parser, out):
        return (p.if_.one(p.string, out).  # support both " " and ' '
                elif_.one(p.decimal, out). # number
                elif_.one({'true' : True, 'false': False, # bool literals
                           'on'  : True, 'off'  : False,
                           'yes' : True, 'no'   : False,  # ic -> ignore case
                           'null': None, 'none' : None}, out, ic=True).
                # bare value until comment/EOL:
                else_.one_or_more(p.chars('^#;\n\r$'), acc=lambda v: p.accumulate(out, v.strip())).
                endif)

    # Lets use aliases, x1 (one), x1_ (one_or_more), x0_ (zero_or_more), etc., for shorter lines:

    @p.subroutine # [section] header
    def section(p: Parser):
        name = Val('')
        return (p.x0_(ws).x1('[').
                x0_(ws).x1_(p.chars('^[]\n\r$'), acc=(name, lambda _: name.rstrip()), nomatch="Empty section name").
                x1(']', nomatch="Expected ']' after section name").x0_(ws).
                x1(nl,  nomatch="Expected newline after section header").
                err_if(Not(name), "Empty section name").
                do(_enter_section, name.value))

    @p.subroutine # key = value
    def key_value(p: Parser):
        key = Val('')
        return (p.x0_(ws).
                x1_(p.chars('^;#=[]\n\r$'), acc=(key, lambda _: key.rstrip())).
                do_if(key, lambda: (p.
                    x1('=', nomatch="Expected '='").err_if(Not(key), "Empty key name").x0_(ws).
                    if_.x1(value, val := Val()).
                        x0_(ws).x0_(p.chars('^\n\r$')).x0_(nl).
                        do(_set_kv, key.value, val.value).
                    else_.err("Invalid key-value pair").endif)))

    while p.is_active and (p.   # main loop:
        x0_(comment_or_empty).  # - skip any comments/empty lines
        x0_1(section).          # - optional section header
        x0_1(key_value)): pass  # - optional key=value pairs

    return cfg
```
[↑ Back to top](#table-of-contents)


## Quick reference
- **Parser:** (`p`) stateful cursor over input with sentinel `END_CHAR`/`EOF`
  - `p.source` input text
  - `p.pos` current position (int)
  - `p.ch` current char (str) or `p.END_CHAR`/`p.EOF` if at or past the end
  - `p.END_CHAR`/`p.EOF` end-of-input sentinel (str: '\uFFFF')
  - `p.save_pos(tag)` - store current position with tag in the Parser's built-in position dictionary, which is separate from the backtrack stack.
  - `p.pop_pos(tag)` - remove and return the stored position for the given tag. Can also return an offset/trimmed slice from the given position.
  - `p.copy(tag, acc)` - copy input from the stored position with the given tag to current position into the given accumulator.
  - `p.copy_from(pos, acc)` - copy input from the given position to current position into the given accumulator.
  - `p.slice(n)` input substring (len=n) from current pos (includes `END_CHAR` as needed)
  - `p.slice_from(start)` input substring from start to current pos (includes `END_CHAR` as needed)
  - `p.slice_behind(n)` input substring (len=n) before current pos (includes `END_CHAR` as needed)
- [Matchers](#matchers): match individual characters or sequences:
  - Literals: `'a'`, `'hello'`,
  - Combination: `('a', 'b', str.isdigit)` - Any of the matchers in the tuple
  - Mapping: `{'true': True, 'false': False}` - maps matched literal to output value passed to accumulator
  - Unary predicate: `str.isalpha` and custom callables with any number of args
  - Negation: `Not(...)`, which negates any matcher (`Not` is treated specially by the parser)
  - Char sets: `In('abc')`, `p.chars('a-zA-Z0-9')`,
  - Subroutine: `@parser_subroutine` (_aliases:_ `@p.subroutine`, `@p.sr`), can be recursive!
- [Quantifiers](#quantifiers): using matchers above to do the actual parsing and accumulation:
  - `one(matcher, *args, *, ic, acc, nomatch, **kwargs)` - match exactly one occurrence of the matcher.
    - `*args` and `**kwargs` are passed to the matcher if it is a subroutine matcher. otherwise they are the accumulator(s).
    - `ic=True` makes matching case-insensitive (or passed to subroutine matcher).
    - `acc=` accumulator(s)
  - `zero_or_one(str.isalpha)`, `one_or_more(...)`, `zero_or_more(...)` - multiple/optional occurrences
  - `repeat(m, n, str.isdigit)` and its aliases: `exactly(n, ...)`, `at_least(n, ...)`, `at_most(n, ...)`
  - Dynamic: `two(...)`, `two_to_five(...)`, `four_or_more(...)`, etc. quantifiers generated on-the-fly and cached in the Parser class as regular methods.
  - Short aliases: `x2(str.isdigit)`, `x2_5(...)`, `x4_(...)`, `x0_(...)`, etc.
  - `p.ws` matcher-quantifier (takes no arguments) that skips any `str.isspace` chars; similar (albeit more efficient) to a more verbose `zero_or_more(str.isspace)`.
- Case-insensitive (ignoring case) matching:
  - Any quantifier with `ic=True` argument
  - Or add `_ic` (long forms) or `i` (short aliases) suffix to quantifier names:
    `one_ic`, `twelve_or_more_ic`, `x2_5i`, etc.
- [Accumulation/emission](#accumulation--emission), passed to quantifiers as plain positional args or `acc=...`:
  - Lists, dicts, sets, anything with `append` or `add` method
  - Convenient scalar value accumulator: `Val` (str, int, float, bool)
  - Multiple sinks at once: `tuple(sink1, sink2, ...)` or `Acc(sink1, sink2, ...)`
  - Callable sinks: `sink(value)`
  - Mapping sinks: `(dict, key, [converter_or_combiner])`
  - `Parser.accumulate` generalizes all of the above
- Side-effects and emission at any point in the parsing tree with `do` and `do_if`:
  - `do(print, 'matched!')` calls any callable with any args
  - `do_if(pred, lambda: print('hello'))` evaluate `pred` and call any callable (with any args) if true
- [Branching and flow](#lookahead-backtracking--flow-control):
  - `if_/elif_/else_/endif` (aliases for lookahead/alt/commit)
  - lookbehind (no consuming): `behind('abc')`
  - peek ahead (no consuming): `peek('abc')`
  - breaks: `break_`, `continue_`, `end`, `fail`, `err`, `back`, `back_ok`
  - conditional breaks: `check`, `fail_if`, `err_if`
- Built-in parser subroutines (accessed through Parser class or instance):
  - `decimal` - int or float with exponent
  - `int_`, `uint` - signed/unsigned base-10 integer
  - `identifier` - XID start/continue, e.g. Python identifiers
  - `string` - quoted strings, w/ custom escapes/quotes and in-line replacements
  - `collection` - generic delimited lists, dicts, etc., w/ generic item-subroutine, custom separators, brackets/no brackets, empty item handling
- Helper classes:
  - `In`, `Not`, `Predicate (P)` - predicates/matchers
  - `Val`, `Acc` - scalar accumulator (string/int/float/bool) and multi-sinks
- Error handling
  - `err(msg)` raises ValueError (or calls your handler) with input context at any point in the parsing tree.
  - `err_if(pred, ...)` raises (or calls your handler) if `pred()` is true at that point.
  - `nomatch='...'` keyword argument in any quantifier raises (or calls your handler) on failed match.
  - `on_err=...` keyword argument in built-in subroutines, e.g. `string`, `collection`.
- FSM parsing
  - Use Parser members `state`, `goto`, `skip_to`, `next`, and Python's `match/case`
  - Examples: built-in `string` and `collection` subroutines are examples of FSM-style parsing
  - `@parser_subroutine_new_stack` forks another parser instance to isolate state to the subroutine.
    Position (but not any other state) is merged back on return. Useful for FSM subroutines to
    avoid modifying the main parser's state.

[↑ Back to top](#table-of-contents)

## Minified Build
A stripped (minified) build can be generated with [utils/minify.py](utils/minify.py). The stripped version doesn't include comments, docstrings, or tracing/debugging support. See [DEV.md](DEV.md) for details.

## Development & Contributing
See [DEV.md](DEV.md) for guidelines. See also [CHANGELOG.md](CHANGELOG.md).

## Thread safety
For its intended use, a `Parser` instance for each parsing task, Parsek should be safe to use in a multi-threaded environment. Some precautions:
- A parser instance should not be shared between threads (unless you provide your own synchronization).
- Debugging/tracing settings are global to the Parser class and affect all threads - debug your parser in a single thread environment.

## License
MIT License – see [License](LICENSE).
