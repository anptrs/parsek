# Copyright (c) 2025 Anton Petersen
# SPDX-License-Identifier: MIT
# This file is part of the Parsek project: https://github.com/anptrs/parsek
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

# pylint: disable=missing-function-docstring,missing-class-docstring
# pylint: disable=line-too-long,too-many-lines,multiple-statements
"""Pure Python, no-dependency, single source file parser combinator library"""
from enum import Enum
from typing import Any, Callable, Mapping

def str_concise(s: str, max_len: int = 10, unicode_ellipsis = False) -> str:
    """Returns a concise version of the string `s` by truncating it to `max_len`
    characters and adding ellipses if needed.

    Args:
        s (str): The input string.
        max_len (int): The maximum length of the output before truncation.
        unicode_ellipsis (bool): If True, use Unicode ellipsis character '…'
            (U+2026) instead of three individual dots, '...'.
    Returns:
        str: The concise version of the string `"Hello, World!"` -> `"Hello, Wo..."`
    """
    if len(s) > max_len:
        s = s[:max_len] + ('…' if unicode_ellipsis else  '...')
    return s

def str_context(s: str, i: int, context_size: int = 10, unicode_ellipsis=True) -> str:
    """Returns a string showing the context around the position `i` in the string `s`.
    The position is marked using a Unicode combining character `_`. Ellipses are added to
    indicate the start and end of the snippet if it's not already at the start or end.

    Args:
        s (str): The input string.
        i (int): The position in the string where the context is needed.
        context_size: Number of characters to show before and after the position `i`.
        unicode_ellipsis (bool): If True, use Unicode ellipsis character '…'
            (U+2026) instead of three individual dots, '...'.
    Returns:
        str: A string with the context and the position marked.
    """
    i = max(0, min(i, (l := len(s)) - 1)) # clamp index to `s`
    start, end = max(i - context_size, 0), min(i + context_size + 1, l)
    # Extract the context around the position `i`
    if not (context_size := len(s := s[start:end])): # pylint: disable=superfluous-parens
        return s
    # Insert the marker: combining character '_' below the letter
    marker_pos = min(i - start, context_size - 1)
    s = s[:marker_pos] + s[marker_pos] + '\u0332' + s[marker_pos + 1:]
    ellipsis = '…' if unicode_ellipsis else  '...'
    if start > 0:
        s = ellipsis + s
    if end < l:
        s = s + ellipsis
    return s

def str_replace(s: str, *args, **kwargs):
    """String replace (like `str.replace(old, new)`) with an additional overload
    for a mapping dict which allows multiple replacements in one call.

    The mapping can also contain callables as replacement values, which will be
    called with any additional `**kwargs`.
    And the mapping key can be a compiled regex pattern (or any object with `sub`).
    """
    if len(args) == 1 and isinstance(args[0], dict):
        for old, new in args[0].items():
            if callable(new):
                new = new(**kwargs)
            s = old.sub(new, s) if hasattr(old, 'sub') else s.replace(old, new)
        return s
    return s.replace(*args, **kwargs)

def add_static(name: str, v):
    """Decorator to add static value to an object (e.g. function)."""
    def decorator(obj):
        setattr(obj, name, v)
        return obj
    return decorator

def parser_subroutine(f):
    """Decorator to mark a function as a parser subroutine."""
    setattr(f, '__parsek_sub', True)
    return f

def parser_subroutine_new_stack(f):
    """Decorator to mark a function as a parser subroutine with a new stack."""
    setattr(f, '__parsek_sub', True)
    setattr(f, '__parsek_new_stack', True)
    return f

def unary(obj):
    """Decorator to disambiguate unary callables. Simply sets obj.__arity = 1 attribute."""
    setattr(obj, '__arity', 1)
    return obj

_BUILTIN_UNARY = {str.isalnum, str.isalpha, str.isascii, str.isdigit, str.islower, str.isspace, str.isupper}
def is_unary(f):
    """Return True if callable `f` effectively takes a single user argument."""
    # NOTE: Avoids using `inspect` for performance reasons.
    # Case 0: does it have __arity attribute?
    if (arity := getattr(f, '__arity', None)) is not None:
        return arity == 1
    # Case 1: f is a built-in unary function (quick check for most used, others in step 4)
    if f in _BUILTIN_UNARY:
        return not hasattr(f, '__self__') # only non bound, e.g., not `"hi".isdigit`
    # Case 2: f has a __code__ attribute (regular functions/lambdas and unbound methods)
    if hasattr(f, '__code__'):
        return 1 == f.__code__.co_argcount - int(hasattr(f, '__self__'))
    # Case 3: f is a callable object (e.g. a class functor) and has __call__
    if hasattr(f, '__call__') and hasattr(f.__call__, '__code__'):
        return 1 == f.__call__.__code__.co_argcount - int(hasattr(f.__call__, '__self__'))
    # Case 4: f is a built-in function or method without a __code__ attribute.
    # Example: str.isdigit -> '($self, /)'
    if (sig := getattr(f, '__text_signature__', None)):
        return 1 == sig.count(',') - int(hasattr(f, '__self__'))
    return False

def default_combiner(old, new):
    """Default combining function."""
    if old is None:
        return new # adopt new value if old is None
    if (append_ := getattr(old, 'append', None)):
        append_(new) # modify in place
        return old
    return (old or new) if isinstance(new, bool) else old + new

def dict_append(dk, v):
    """Append a value to a dictionary. dk must be a (d, key [, converter/combiner]) tuple."""
    try:
        key = key if isinstance(key := dk[1], str) else str(key)
        old_v = (d := dk[0]).get(key)
        combiner = default_combiner
        if len(dk) > 2 and (fn := dk[2]) : # has converter/combiner
            try: # try as a converter, single argument (we could use is_unary here, but it's heavier)
                v = fn(v) # try as converter (most likely case)
            except TypeError:
                combiner = fn # try as a combiner
        d[key] = combiner(old_v, v) # combine values
    except (IndexError, TypeError, KeyError, ValueError, ImportError) as e:
        raise ValueError("Dictionary update failed: expected result tuple"
                         f" (dict, key, [converter/combiner]), got: {dk!r}") from e

def dict_update(d, v):
    """Updates dict `d` with the given value `v`, which must be a
    `(key, value [, converter/combiner])` tuple (or a sequence of those) or a Mapping."""
    if isinstance(v, tuple) and 2 <= len(v) <= 3:
        dict_append((d, v[0], *v[2:]), v[1])
    elif isinstance(v, Mapping):
        for key, new_v in v.items():
            d[key] = default_combiner(d.get(key), new_v)
    elif hasattr(v, '__iter__'): # iterable of (k, v [, converter/combiner]) pairs
        for vv in v:
            dict_append((d, vv[0], *vv[2:]), vv[1])
    else:
        raise ValueError("Dictionary update failed: mapping target requires (key, value)"
                         f" tuple or Mapping, got: {v!r}")

class Predicate:
    """Predicate that evaluates on truthiness.

    Captures optional args/kwargs. Use where a boolean predicate is
    expected: `do_if(Predicate(fn, *args, **kwargs), ...)`

    Note: if `fn` is not callable, it will be evaluated as bool(fn) (ignoring args/kwargs) every time.
    This allows for example to track any reference value, e.g., a list or Val instance.
    """
    __slots__ = ('f', 'args', 'kwargs')
    def __init__(self, f, *args, **kwargs):
        self.f = f
        self.args = args
        self.kwargs = kwargs

    def __bool__(self):
        return bool(self.f(*self.args, **self.kwargs)) if callable(self.f) else bool(self.f)

    def __call__(self, *args, **kwargs): # Optional direct eval; if no args given, use captured ones
        if args or kwargs:
            return bool(self.f(*args, **kwargs)) if callable(self.f) else bool(self.f)
        return bool(self.f(*self.args, **self.kwargs)) if callable(self.f) else bool(self.f)

    if __debug__:
        def trace_repr(self):
            # pylint: disable=protected-access
            return (f"∀ {Parser._matcher_to_str(self.f, self.args, self.kwargs)}"
                    if Parser._trace else repr(self))

class Not:
    """Negation. Example: `p.one(Not(In('abc')))...` `Not` is treated specially
    as well as optimized for by the Parser.

    Use `Not` as the matcher in expressions (in one(), zero_or_more(), and others).

    `Not` can also be used as a general-purpose negation predicate:
    ```python
    p.one('a', ok := Val(False))...fail_if(Not(ok))...
    # here `ok` will be flipped to True if 'a' was found, and some
    # farther branch will fail if 'a' was not found.
    ```
    If there are multiple arguments, they are ORed together and the result negated.
    The arguments are evaluated as callables if they are callable, otherwise as bool(arg).
    """
    # Negates everything that one() accepts: strings, tuples, functors, etc.
    __slots__ = ('f',)
    def __init__(self, f, *args):   self.f = (f, *args) if args else f
    def __repr__(self):             return f"{self.__class__.__name__}({self.f!r})"
    def __bool__(self):             return self.__call__()
    def __call__(self):
        if isinstance(f := self.f, tuple):
            return not any((bool(ff()) if callable(ff) else bool(ff)) for ff in f)
        return not (bool(f()) if callable(f) else bool(f))

    @staticmethod
    def crack(f):   return (True, f.f) if isinstance(f, Not) else (False, f)

class Raw(Not):
    def __init__(self, f=None): super().__init__(f)

@unary
class In:
    """String as a character set. Example: `p.one(In('abc'))...`
    Equivalent to: `p.one(('a', 'b', 'c'))...`
    `In` is marginally more efficient than using a tuple and easier to type."""
    __slots__ = ('s',)
    def __init__(self, s):     self.s = s
    def __call__(self, v):     return v in self.s
    def __contains__(self, v): return v in self.s
    def __repr__(self):        return f"In({self.s!r})"
    if __debug__:
        def trace_repr(self):  return f"in {self.s!r}"

@unary
class Range:
    """Inclusive range of chars. Example: `p.one(Range('a', 'z'))...`"""
    __slots__ = ('lo', 'hi')
    def __init__(self, lo, hi):
        if lo > hi:  lo, hi = hi, lo  # normalize order: lo <= hi
        self.lo = lo;  self.hi = hi
    def __call__(self, v):       return self.lo <= v <= self.hi
    def __contains__(self, v):   return self.lo <= v <= self.hi
    def __len__(self):           return ord(self.hi) - ord(self.lo) + 1
    def __repr__(self):          return f"Range({self.lo!r}, {self.hi!r})"
    if __debug__:
        def trace_repr(self):    return f"in [{self.lo!r}..{self.hi!r}]"

class Val:
    """Variant-type accumulator for basic scalar types: str, int, float, bool."""
    __slots__ = ('v', 'combiner')
    def __init__(self, v=None, combiner=None):
        self.v = v
        self.combiner = combiner
    def __repr__(self):   return f"Val({self.v!r})"
    def __bool__(self):   return bool(self.v)
    def __len__(self):    return len(self.v) if hasattr(self.v, '__len__') else 0
    def __eq__(self, v):  return self.v == (v.v if isinstance(v, Val) else v)
    def __hash__(self):   return hash(self.v)
    def __str__(self):    return str(self.v)
    def __iadd__(self, v):return self.append(v)

    @property
    def value(self):      return self.v
    @value.setter
    def value(self, v):   self.v = v

    @property
    def is_bool(self):  return isinstance(self.v, bool)
    @property
    def is_float(self): return isinstance(self.v, float)
    @property
    def is_int(self):   return isinstance(self.v, int) and not isinstance(self.v, bool)
    @property
    def is_none(self):  return self.v is None
    @property
    def is_str(self):   return isinstance(self.v, str)
    @property
    def is_scalar(self): return isinstance(self.v, (int, float, str)) # note: bool(int) so also scalar

    def copy(self):
        """Returns a copy of this Val instance."""
        return Val(self.v, self.combiner)

    def clear(self, *_):
        """Clears the value based on its type. Returns `self`(chainable)."""
        if (v := self.v) is not None:
            self.v = type(v)() # default c-tor
        return self

    def inc(self, step=1):
        """Increment numeric value by `step` (default 1). If value is None, it will be set to `step`.
        Flips bool to True if step > 0, False if step < 0, or leaves as is if step == 0.
        Returns `self`(chainable)."""
        if (v := self.v) is None:
            self.v = step
        elif isinstance(v, bool): # check first because bool is a subclass of int
            self.v = True if step > 0 else (False if step < 0 else v)
        elif isinstance(v, (int, float)):
            self.v += step
        else:
            raise ValueError(f"Cannot increment non-numeric Val value: {v!r}")
        return self
    def dec(self, step=1):
        """Decrement numeric value by `step` (default 1). If value is None, it will be set to `-step`.
        Flips bool to False if step > 0, True if step < 0, or leaves as is if step == 0.
        Returns `self`(chainable)."""
        return self.inc(-step)

    def reset(self, *_):
        """Set the value to None. Returns `self`(chainable)."""
        self.v = None
        return self

    def set(self, v):
        """Set/convert value according to current Val type. If current type is None, adopt the type of `value`.
        *Note:* `set(None)` is the same as `clear()`.
        Returns `self`(chainable)."""
        if v is None:
            return self.clear()

        if self.is_none: # Adopt type if currently None
            self.v = v
        else: # For all other types convert to current type and replace
            self.v = type(self.v)(v)
        return self

    def append(self, v):
        """Append/accumulate a value to the current Val.
        If a combiner is set, it will be used to combine the current value with the new value.
        If the current value is None, it will be set to the new value.
        Accumulation behavior (no combiner) depends on the current Val type:
        - str: the new value will be concatenated.
        - bool: new value converted to bool and ORed with the old
        - int and float: the new value is added to the old value, promoting int to float as needed.
        - other (custom): `.append(value)` method will be called if it exists or the value will be replaced outright.
        Returns `self`(chainable)."""
        if self.combiner is not None:
            self.v = self.combiner(self.v, v)
            return self
        if (v_ := self.v) is None:
            self.v = v
        elif isinstance(v_, str):
            self.v += (v if isinstance(v, str) else str(v) if v is not None else '')
        elif isinstance(v_, bool): # check first because bool is a subclass of int
            self.v = v_ or bool(v)
        elif isinstance(v_, int):
            self.v += v if isinstance(v, (int, float)) else int(v)
        elif isinstance(v_, float):
            self.v += v if isinstance(v, (int, float)) else float(v)
        elif (append_ := getattr(v_, 'append', None)):
            append_(v) # pylint: disable=not-callable
        else:
            self.v = v
        return self

    def apply(self, fn, *args, **kwargs):
        """Generic transform: `self.v = fn(self.v, *args, **kwargs)`. Returns `self`(chainable).
        Notes:
        - If fn mutates in place and returns None (common pattern), your value becomes None.
            Wrap such calls: `r.apply(lambda v: fn(v) or v)`.
        - Prefer dedicated Val helpers (strip / replace / lower, etc.) when available.
        - Use functools.partial to pre-bind arguments.

        Examples:
        ```python
        from functools import partial

        p = Parser(input)
        r = p.Val()
        ...p.do(r.apply, str.title)
        ...p.do(r.apply, lambda s: s.strip().upper())
        ...p.do(r.apply, partial(str.replace, '*', '-'))
        # above `partial` not really necessary, and this will work the same:
        ...p.do(r, str.replace, '*', '-')
        ```
        *Note:* Parser is aware of the Val type and treats it specially, so you can drop the `.apply` and just pass in the Val instance.
        ```python
        ...p.do(r, str.title) # Parser will call r.apply(str.title)
        ...p.do(r.title)      # using available Val.title() instead
        ```
        """
        self.v = fn(self.v, *args, **kwargs)
        return self

    def use(self, combiner: Callable[[Any, Any], Any] | None):
        """Sets the combiner function for this instance. Which is used by the `append` method.
        Define your own combiners to this signature, `def combiner(prev, new): -> combined`.
        There are a few basic combiners available:
        - `Val.reduce_and`: logical AND
        - `Val.reduce_or`: logical OR
        - `Val.reduce_xor`: logical XOR

        Returns `self`(chainable).
        """
        self.combiner = combiner
        return self

    # Convenience methods for string manipulation
    @staticmethod
    def _str_transform(op: str | Callable, name=None):
        str_meth = getattr(str, op) if (is_name := isinstance(op, str)) else None
        public_name = name or (op if is_name else getattr(op, '__name__', 'transform'))

        def apply_meth(s, *args, **kwargs):
            if type(s) is str: # check if not a subclass; pylint: disable=unidiomatic-typecheck
                return str_meth(s, *args, **kwargs)
            return getattr(s, op)(*args, **kwargs) # Subclass: respect override
        fn = apply_meth if is_name else op

        def _m(self, *args, **kwargs):
            if isinstance(v := self.v, str):
                self.v = fn(v, *args, **kwargs)
            elif v is not None:
                raise ValueError(f"{public_name}() valid only when value is str or None (have {type(v).__name__})")
            return self

        _m.__name__ = public_name
        _m.__qualname__ = f"Val.{public_name}"
        _m.__doc__ = f"Apply {public_name} to contained string value."
        return _m

    casefold = _str_transform.__func__('casefold')
    lower    = _str_transform.__func__('lower')
    lstrip   = _str_transform.__func__('lstrip')
    rstrip   = _str_transform.__func__('rstrip')
    strip    = _str_transform.__func__('strip')
    title    = _str_transform.__func__('title')
    upper    = _str_transform.__func__('upper')
    replace  = _str_transform.__func__(str_replace, name='replace')

    # Convenience value processors, accumulators, reducers, and combiners
    @staticmethod
    def reduce_and(prev, new):  return prev and new
    @staticmethod
    def reduce_or(prev, new):   return prev or new
    @staticmethod
    def reduce_xor(prev, new):  return prev != new

    if __debug__:
        def trace_repr(self):
            # pylint: disable=protected-access
            return f"𝒱 {Parser._v_to_str(self.v)}" if Parser._trace else repr(self)

class Acc:
    """A set of accumulators, used to collect multiple results in a single pass.
    Acc can contain items of any type accepted by Parser.accumulate().
    Example:
    ```python
    p = Parser("hello   World")
    s, l, b = Val(), [], Val(False)
    p.one('hello', Acc(s, l, b))
    assert s == 'hello' and l == ['hello'] and b == True
    # NOTE: Parser interprets any tuple where 1st item is a Val as an Acc:
    p.one_or_more(str.isspace).one('world', (s, l, b), ic=True) # dropping Acc works the same as above
    assert s == 'helloWorld' and l == ['hello', 'World'] and b == True
    ```
    """
    __slots__ = ('results',)
    def __init__(self, *results: Val):   self.results = results
    def __len__(self):    return len(self.results)
    def __iter__(self):   return iter(self.results)
    def __repr__(self):   return f"Acc({', '.join(repr(r) for r in self.results)})"


class Parser:
    """ String parser allows expression-based parsing and FSM-based at the same time.
    Sentinel character 'END_CHAR' is always "added" (not actually added) to the end of the input.
    While the expression-based parsing functionality is particularly attractive, sometimes the FSM parsing is more effective.
        Setup loop for FSM parsing:
        ```
        p = Parser(source)
        while not p.is_end:
            ch = p.ch
            p.next()
            match p.state:
                case State.INITIAL:
                    if ch == '-':
                        p.state = State.MINUS
                    elif ch.isdigit():
                        p.skip_to(State.INT)
        ```

        Class Variables:
            - END_CHAR (str): Sentinel character used to mark the end of the string.
            - PARSE_LIMIT (int): Limit the number of parsing steps to prevent infinite loops.
    """
    In  = In
    Not = Not
    P   = Predicate
    Predicate = Predicate
    Range = Range
    Val = Val
    Acc = Acc

    END_CHAR     = '\uFFFF'
    EOF          = END_CHAR # alias
    END_STATE    = type('_EndState', (), {'__repr__': lambda self: 'END_STATE'})()
    NOT_END_CHAR = Not(END_CHAR)
    NOT_EOF      = NOT_END_CHAR # alias
    PARSE_LIMIT  = 100000

    # First twenty cardinal number words
    NUM_WORDS = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
        'nineteen': 19, 'twenty': 20 }

    sr = staticmethod(parser_subroutine)
    subroutine = staticmethod(parser_subroutine)
    subroutine_new_stack = staticmethod(parser_subroutine_new_stack)

    _cache_chars = {}      # cache for the Parser.chars() factory

    class Branch:
        __slots__ = ('parent', )
        def __init__(self, parent):    self.parent = parent
        def __getattr__(self, name):   return self
        def __bool__(self):            return self.is_ok
        def __call__(self, *a, **k):   return self
        def __repr__(self):            return f"{self.__class__.__name__}(parent={self.parent!r})"

    class Shunt(Branch): # Represents inactive branch of the expression
        is_ok     = True
        is_active = True
        endif     = property(lambda self: self.parent)
        endif_    = endif
        commit    = endif
        merge     = endif
    Shunt.if_       = property(Shunt) # defining these outside the class eliminates the need for lambdas
    Shunt.lookahead = property(Shunt)

    class Fail(Branch): # Represents false branch of the expression
        @property
        def elif_(self):
            self.parent.backtrack()
            return self.parent.if_
        else_     = property(lambda self: self.parent._bkt_else) # pylint: disable=protected-access
        endif     = property(lambda self: self.parent.backtrack())

        is_ok     = False
        is_active = False
        alt       = else_
        commit    = endif
        endif_    = endif
        merge     = endif
    Fail.if_       = property(Fail) # defining these outside the class eliminates the need for lambdas
    Fail._bkt_else = property(Fail) # pylint: disable=protected-access
    Fail.lookahead = property(Fail)

    class Stop: # Base for all stops
        __slots__ = ()
        is_ok = False
        is_active = False
        def __bool__(self):  return self.is_ok
        def __getattr__(self, _name):  return self
        def __call__(self, *_args, **_kwargs):  return self

    class Break(Stop): # Breaks the current expression
        __slots__ = ('parent', 'depth', 'lwm')
        def __init__(self, parent):
            self.parent = parent
            self.depth = 1
            self.lwm = 0

        def _close(self): self.parent.commit # pylint: disable=pointless-statement

        @property
        def if_(self):
            self.depth += 1
            return self
        @property
        def endif(self):
            if (depth := self.depth - 1) <= self.lwm:
                self._close()
                self.lwm = depth - 1 # lowest watermark, so we don't backtrack what we never put on the stack
            self.depth = depth
            return self
        commit    = endif
        endif_    = endif
        lookahead = if_
        merge     = endif

    class Back(Break):
        is_ok = False
        def _close(self): self.parent.backtrack()

    class BackOk(Break):
        is_ok = True
        def _close(self): self.parent.backtrack()

    class Continue(Break):
        is_ok = True

    class End(Stop):
        is_ok = True

    if __debug__:
        __slots__ = ('source', 'state', 'pos', '_skip', 'len', '_lookahead_stack', '_pos_dict', 'tracing', '_lsd')
    else:
        __slots__ = ('source', 'state', 'pos', '_skip', 'len', '_lookahead_stack', '_pos_dict')
    def __init__(self, source, state=None, pos:int=0, skip=False):
        """ Initialize the parser with the source string.
        Args:
            source: The input string to be parsed.
            state: The initial FSM state of the parser. Defaults to None.
            pos (int): The current position in the source string. Defaults to 0.
            skip (bool): Skip state, if `True` next() skips the next character. Defaults to `False`.
        """
        self.source = source
        self.state = state
        self.pos = pos
        self._skip = skip
        self.len = len(self.source)
        self._lookahead_stack = []
        self._pos_dict = None
        if __debug__:
            setattr(self, 'tracing', tracing := bool(self.__class__._trace))
            if tracing:
                setattr(self, '_lsd', 0) # lookahead stack depth of parent parser (for tracing, set by forked parsers)
                self.trace(2, f"+ new parser: {str_concise(source[self.pos:], 40, True)!r}")

    def _fork(self):
        if __debug__:
            if self.tracing:
                p = self.__class__(self.source, self.state, self.pos, self._skip)
                setattr(p, '_lsd', self._lsd + len(self._lookahead_stack)) # lookahead stack depth of parent parser
                return p
        return self.__class__(self.source, self.state, self.pos, self._skip)

    def _fork_behind(self):
        if __debug__:
            if self.tracing:
                p = Lookbehind(self)
                setattr(p, '_lsd', self._lsd + len(self._lookahead_stack)) # lookahead stack depth of parent parser
                return p
        return Lookbehind(self)


    def _join(self, other):
        self.pos = other.pos

    def __bool__(self): return True # always true, represents a successful parse branch
    def __call__(self): return self
    def __repr__(self):
        return (f"{self.__class__.__name__}({f'state={self.state}, ' if self.state is not None else ''}"
                f"pos={self.pos}:'{str_context(self.source, self.pos)}')")

    @property
    def ch(self):
        """ Returns the current character in the source string or the sentinel (`Parser.END_CHAR`) if at or past the end. """
        return self.source[self.pos] if self.pos < self.len else self.END_CHAR
    @property
    def is_end(self):
        """ Returns True if the parser has reached (or past) the end of the source string. """
        return self.pos >= self.len
    @property
    def is_end_state(self):
        """ Returns True if the parser is in `Parser.END_STATE` state. """
        return self.state is Parser.END_STATE
    @property
    def is_past_end(self):
        """ Returns True if the parser has moved past the end of the source string. This is when END_CHAR is consumed, e.g., with `one(p.END_CHAR)`."""
        return self.pos > self.len
    @property
    def is_ok(self):
        """ Returns True if the branch (expression) is in OK, successfully matching, state. Same as bool(parser). (supported by chain expressions)."""
        return True # always true, represents a successful parse branch
    @property
    def is_active(self):
        """ Alias for `not Parser.is_end_state` (supported by chain expressions). """
        return not self.is_end_state

    def next(self, n=1):
        if self._skip:
            self._skip = False
            return self
        self.pos = p if (p := self.pos + n) <= self.len else (self.len + 1)
        return self
    def _next(self):
        self.pos = p if (p := self.pos + 1) <= self.len else (self.len + 1)
    def skip(self):
        self._skip = True
        return self
    def skip_to(self, state):
        self._skip = True
        self.state = state
        return self
    def goto(self, state):
        self._skip = False
        self.state = state
        return self
    def err(self, msg):
        if callable(msg):
            msg(self)
            return self.fail
        raise ValueError(f"{msg} at: {str_context(self.source, self.pos)}")
    def err_if(self, predicate, msg):
        if callable(predicate):  predicate = predicate()
        return self.err(msg) if predicate else self


    def save_pos(self, key):
        """ Saves current position under 'key' for later retrieval """
        if (d := self._pos_dict) is None:
            d = self._pos_dict = {}
        d[key] = self.pos
        return self
    def pop_pos(self, key, as_str: bool = None, offset: int | tuple = None):
        """ Removes and returns the position saved under 'key'. None if not found
            Also can return as string if either as_str is True or offset is not None.
            Note, to include current position `offset` should be (start_offset, 1)
        """
        if as_str or offset is not None:
            if (d := self._pos_dict) and (pos := d.pop(key, None)) is not None:
                b_off = offset if isinstance(offset, int) and offset >= 0 else offset[0] if isinstance(offset, tuple) else 0
                e_off = offset if isinstance(offset, int) and offset <  0 else offset[1] if isinstance(offset, tuple) else 0
                return self.source[pos + b_off:self.pos + e_off]
            return None
        return self._pos_dict.pop(key, None) if (d := self._pos_dict) else None
    def copy(self, key, out, pop=True, on_err=err):
        """Copies the text from the saved position under 'key' to the current position (not including) into 'out'."""
        if (d := self._pos_dict) and (found := d.get(key)) is not None:
            self.copy_from(found, out)
            if pop: d.pop(key)
        elif on_err:
            self.on_err(on_err, f"Position '{key}' not found in saved positions")
        return self
    def copy_from(self, start: int, out):
        """ Copies the text from 'start' position to the current position (not including) into 'out' """
        if out is not None:   Parser.accumulate(out, self.source[start:self.pos])

    @property
    def lookahead(self):
        """(*Alias:* `if_`) Starts a lookahead (speculative) branch. Must always be followed by an `alt/merge`, or
        `commit/backtrack`.

        A lookahead records the current input position on an internal stack and then allows you to try a sequence of
        matches. Every lookahead you start MUST be closed by exactly one of:
          - `commit` (alias: `endif` | `endif_` | `merge`) -> keep the new position
          - `backtrack()` -> revert to the saved position
          - `alt` (alias: `else`) -> create an alternative branch (exactly one alt per lookahead)
        The lookahead / alt pair forms a two-branch construct similar to IF / ELSE.
        Nesting is allowed. For multi-way branching use the
        if_ / elif_ / else_ / endif form (which adds possibility of multiple elif_ branches).

        Returns:
            self (Parser) for chaining, or Parser.End() if in END_STATE.
        """
        if self.is_end_state:  return Parser.End()
        if __debug__:
            if self.tracing: self.trace(5, f"? lookahead at {self.pos}:'{self.ch}'")
        self._lookahead_stack.append(self.pos)
        return self
    @property
    def commit(self):
        if self.is_end_state:  return Parser.End()
        if __debug__:
            assert self._lookahead_stack, "Lookahead stack is empty"
            if self.tracing and self._lookahead_stack[-1] >= 0: # pos <0 are fake lookaheads pushed by Fail._bkt_else
                self.trace(5, f"✔ commit to {self.pos}:'{self.ch}'")
        self._lookahead_stack.pop()
        return self
    @property
    def alt(self):
        return Parser.End() if self.commit.is_end_state else Parser.Shunt(self)
    @property
    def is_backtrackable(self):
        return len(self._lookahead_stack) > 0
    def backtrack(self):
        if self.is_end_state:  return Parser.End()
        assert self._lookahead_stack, "Lookahead stack is empty"
        if (p := self._lookahead_stack.pop()) >= 0:
            self.pos = p
            if __debug__:
                if self.tracing: self.trace(5, f"↩ backtrack to {self.pos}:'{self.ch}'")
        else:
            return Parser.Fail(self)
        return self
    @property
    def _bkt_else(self):
        # This is only called from the Fail.else_ (or Fail.alt) branch
        rv = self.backtrack()
        self._lookahead_stack.append(-1) # push fake lookahead
        return rv
    @property
    def fail(self):
        """Fails the current branch."""
        return Parser.End() if self.is_end_state else Parser.Fail(self)
    def fail_if(self, predicate, *args, **kwargs):
        """Fails the current branch if `predicate` or `predicate(*args, **kwargs)` (callable) is True."""
        if self.is_end_state:    return Parser.End()
        if callable(predicate):  predicate = predicate(*args, **kwargs)
        return Parser.Fail(self) if predicate else self
    @property
    def back(self):
        """Backtracks all uncommitted lookahead branches of the expression; returns `False` for the whole expression."""
        if self.is_end_state:   return Parser.End()
        if __debug__: self.trace(3, "↰ back")
        return Parser.Back(self)
    @property
    def back_ok(self):
        """Backtracks all uncommitted lookahead branches; returns `True` for the whole expression."""
        if self.is_end_state:   return Parser.End()
        if __debug__: self.trace(3, "↰ₒₖ back_ok")
        return Parser.BackOk(self)
    @property
    def break_(self):
        """Stops the current expression by returning a `Stop` object (evaluates to `False` for the whole expression).
        Commits all uncommitted lookahead branches of the host expression. Returns `False` for the whole expression.
        ```python
        p.if_.one('STOP').break_.else_.one('more matching').endif # does not backtrack the 'STOP'.
        p.if_.one('STOP').back.else_.one('more matching').endif   # backtracks the 'STOP'.
        ```
        """
        if self.is_end_state:   return Parser.End()
        if __debug__: self.trace(3, "↴ break")
        return Parser.Break(self)
    @property
    def continue_(self):
        """Companion to `break_`: stops the current expression, while committing all lookahead branches.
        Returns True for the whole expression."""
        if self.is_end_state:   return Parser.End()
        if __debug__: self.trace(3, "↻ continue")
        return Parser.Continue(self)
    @property
    def end(self):
        """Put Parser in END_STATE, clear the lookahead stack."""
        if __debug__: self.trace(2, "⏹ end")
        self.state = Parser.END_STATE
        self._lookahead_stack.clear()
        return  self
    if_ = lookahead
    elif_ = alt
    else_ = alt
    endif  = commit
    endif_ = commit
    merge  = commit

    def do(self, f, *args, **kwargs):
        """Calls the function `f` with `args` and `kwargs`.
        Use for any side effects, like setting a result, emitting, printing, etc.
        For example to print a message (for debug): `do(print, "Hello, World!")`.

        `do()` will passthrough the returned Parser object (e.g., Parser, Branch, Stop) if `f` returns one. This allows you to
        splice in additional behavior to modify the parsing process, see `do_if()` for an example.
        """
        if __debug__:
            if self.tracing:
                self.trace(2, f"↑ do {Parser._f_call_to_str(f, args, kwargs)}")

        if isinstance(f, Val):
            f.apply(*args, **kwargs)
        else:
            if isinstance(r := f(*args, **kwargs), (Parser, Parser.Branch, Parser.Stop)):
                return r
        return self

    def do_if(self, predicate, f, *args, **kwargs):
        """Calls the function `f` with `args` and `kwargs` if `predicate` is True. Apart from checking the predicate it behaves the same as `do()`.
        You can do complex patterns with this:
        ```python
        p = Parser('!hello world')
        p.if_.one('!', flag := Val(False)).endif.do_if(flag, lambda: p.if_.one('hello').endif).ws.one('world')
        # or have conditional fail, break, or whatever:
        p.if_. ... .do_if(flag, p.fail) ... .do_if(flag, p.break_)
        ```
        You can use the provided `Predicate` class to create more complex conditions:
        ```python
        p.do_if(Predicate(lambda: flag and other_flag), p.fail)
        # or use a more concise P class alias for Predicate:
        p.do_if(p.P(lambda: flag and other_flag), p.fail)
        ```
        """
        if callable(predicate):  predicate = predicate()
        return self.do(f, *args, **kwargs) if predicate else self

    def check(self, f, *args, **kwargs):
        """Fails the branch with `Parser.Fail` if `f(*args, **kwargs)` returns a truthy False. Otherwise returns self. This is in essence an assertion.
        For example to check that the value is truthy: `p....check(bool, some_value)...`
        """
        if __debug__:
            if self.tracing:
                self.trace(3, f"↑ check {Parser._f_call_to_str(f, args, kwargs)}")
        r = f.apply(*args, **kwargs) if isinstance(f, Val) else f(*args, **kwargs)
        return self if r else Parser.Fail(self)

    def slice(self, len_of_slice):
        """Returns the forward source slice (from current pos to current pos +
        len_of_slice) and adds sentinel `END_CHAR` at the end if needed."""
        if (end := self.pos + len_of_slice) > self.len:
            return self.source[self.pos:] + self.END_CHAR
        return self.source[self.pos:end]

    def slice_behind(self, len_of_slice):
        """Returns the backward source slice, from (current pos - len_of_slice) to current pos (not including).
        Adds sentinel `END_CHAR` at the end if `.is_past_end is True`
        """
        s = self.source[max(0, self.pos - len_of_slice):self.pos]
        if self.pos > self.len:
            s += self.END_CHAR
        return s

    def slice_from(self, start):
        """Returns the source slice from given `start` to the current pos.
        Adds sentinel `END_CHAR` at the end as needed."""
        if self.pos > self.len:
            return self.source[start:] + self.END_CHAR
        return self.source[start:self.pos]

    @property
    def ws(self):
        """Skip whitespace characters (as defined by str.isspace) from the current position."""
        while self.ch.isspace():
            self._next()
        return self

    def behind(self, f, *args, nomatch = None, **kwargs):
        """Matches `f` behind the current position, without changing the current position.
        - If `f` matches, the parser position is unchanged and returns self.
        - If `f` does not match, the parser position is unchanged and returns `Parser.Fail`.
        - If `nomatch` is provided, `err(nomatch)` is called on no match.

        Behind is useful to find context around the current position, e.g., word boundaries, prefixes, etc.
        """
        if self.is_end_state:  return Parser.End()
        if self.is_past_end:   return Parser.Fail(self) # can't look behind past the end
        p = self._fork_behind()
        result = kwargs.pop('acc', None)
        f_, has_params = p._dispatch(f, kwargs) #pylint: disable=protected-access
        if f_(args, kwargs) if has_params else f_(): #pylint: disable=no-value-for-parameter
            if not has_params and args:
                result = ((result, *args) if result is not None else Acc(*args))
            p.copy_from(0, result)
        else:
            if nomatch is not None:
                self.err(nomatch)
            return Parser.Fail(self)
        return self

    def one(self, f, *args, nomatch = None, **kwargs):
        """ Match single occurrence of matcher `f` at the current position. Returns `self` on
        success, `Parser.Fail` on no match.

        Args:
            f: The matcher to apply. Can be one of
                - A string or tuple of strings: matches exactly.
                - A unary callable called with current character: matches if callable returns truthy.
                - A callable with more than one argument: matches if f(p.ch, *args, **kwargs) truthy.
                - Parser subroutine: a function that takes (parser, *args, **kwargs) and attempts
                  to match at the current position. The result of the subroutine is converted to bool
                  to determine success. Note: Break/Continue/Back/BackOk are not propagated out of
                  the subroutine.
                - Mapping (dict): matches if current sequence/character is a key in the dict, and
                  sets the value as result.
                - List or set: matches if current sequence/character is in the collection.
                - Not(...): Negates any of the contained matchers: matches if the contained matcher
                  does NOT match at the current position and advances parser by one character
                  returning True. If the contained matcher matches, returns Parser.Fail without
                  advancing the parser.
                - tuple of the above: matches if any of the items match. (can be nested further)
            *args: Additional positional arguments passed to `f` if it accepts them. Otherwise
                the args are used as accumulators for the matched text and are treated the same
                as if passed in `acc=` kwarg. `acc` is still processed first.
            nomatch (str|callable): If provided, calls `err(nomatch)` on no match. see `err()`
                for details.
            ic (bool): If True then the match ignores case (IC). For subroutines this is passed in
                kwargs.
            acc: Accumulator(s) to accumulate the matched text into. Never passed to `f`. This
                can be a single accumulator or Acc instance containing multiple accumulators.
                Note if acc is a tuple where the first item is a Val instance, Parser will
                interpret the whole tuple as an Acc instance. For possible accumulators see
                `Parser.accumulate()`.

                *Note,* if your matcher `f` is not a subroutine or unary, you don't have to
                use `acc`, you can just pass the accumulators as plain positional args, e.g.,
                `p.one(str.isdigit, l := [], r := Val(0))`; here `l` and `r` will receive the
                matched text. `l` will get a character and `r` will get a converted int value.

                *Note,* that acc receives the matched text, regardless of what `f` emits.
            **kwargs: Additional keyword arguments passed to `f`.

        """
        if self.is_end_state:  return Parser.End()
        start = self.pos
        result = kwargs.pop('acc', None)
        f_, has_params = self._dispatch(f, kwargs)
        # result of matchers is converted to bool, so matcher's Break/Continue/Back/BackOk stops are not propagated out of the subroutine
        if f_(args, kwargs) if has_params else f_(): #pylint: disable=no-value-for-parameter
            if not has_params and args:
                result = ((result, *args) if result is not None else Acc(*args))
            self.copy_from(start, result)
        else:
            if nomatch is not None:
                self.err(nomatch)
            return Parser.Fail(self)
        return self

    def get_one_ctx(self, f, *args, nomatch = None, **kwargs):
        # Makes a reusable context for one_with_ctx()
        return [self._dispatch(f, kwargs), nomatch, args, kwargs]

    def one_with_ctx(self, ctx):
        # one() that uses context returned by get_one_ctx(), to be used in loops, otherwise the same as one()
        (f_, has_params), nomatch, args, kwargs = ctx
        start = self.pos
        if f_(args, kwargs) if has_params else f_():
            result = None
            if not has_params and args:
                result = Acc(*args)
            self.copy_from(start, result)
        else:
            if nomatch is not None:
                self.err(nomatch)
            return Parser.Fail(self)
        return self

    def one_or_more(self, f, *args, **kwargs):
        if self.is_end_state:  return Parser.End()
        if __debug__:
            if self.tracing: self.trace(4, f"one_or_more({self._matcher_to_str(f)})")
        start = self.pos
        result = kwargs.pop('acc', None)
        ctx = self.get_one_ctx(f, *args, **kwargs)
        if not (ret := self.one_with_ctx(ctx)):
            return ret
        ctx[1] = None # remove nomatch since we found at least one match (see get_one_ctx() for why ctx[1])
        ret, _ = self._match_more(ctx)
        self.copy_from(start, result)
        return ret

    def peek(self, f, *args, **kwargs):
        """Peeks ahead to see if `f` matches at the current position without consuming any input.
        If `f` matches, the parser position is unchanged and returns self (True).
        If `f` does not match, the parser position is unchanged and returns `Parser.Fail`.
        """
        ret = self.lookahead.one(f, *args, **kwargs)
        self.backtrack()
        return ret

    def zero_or_more(self, f, *args, **kwargs):
        if self.is_end_state:  return Parser.End()
        if __debug__:
            if self.tracing: self.trace(4, f"zero_or_more({self._matcher_to_str(f)})")
        start = self.pos
        result = kwargs.pop('acc', None)
        ctx = self.get_one_ctx(f, *args, **kwargs)
        ret, k = self._match_more(ctx)
        if k: # (ret and k) copy result if there's at least one match
            self.copy_from(start, result)
        return ret

    def zero_or_one(self, f, *args, **kwargs):
        if self.is_end_state:  return Parser.End()
        if __debug__:
            if self.tracing: self.trace(4, f"zero_or_one({self._matcher_to_str(f)})")
        if self.lookahead.one(f, *args, **kwargs).is_ok:
            return self.commit
        # self.copy_from(self.pos, kwargs.get('acc', None)) # set/append '' to result if no match
        return self.backtrack()

    def repeat(self, min_count: int, max_count: int, f, *args, **kwargs):
        if self.is_end_state:  return Parser.End()
        if __debug__:
            if self.tracing: self.trace(4, f"repeat({min_count}, {max_count}, {self._matcher_to_str(f)})")
        start = self.pos
        result = kwargs.pop('acc', None)
        ctx = self.get_one_ctx(f, *args, **kwargs)
        i = 0
        p = self.lookahead
        while i < max_count and p.one_with_ctx(ctx).is_active:
            i += 1
            if i > Parser.PARSE_LIMIT:  raise ValueError("Infinite loop or input too long")

        if i >= min_count:
            if i: self.copy_from(start, result) # copy only if we matched at least once
            return self.commit
        return self.backtrack().fail

    # LOOP/MATCH ALIASES:
    def at_least(self, count: int, f, *args, **kwargs):
        """ Alias for `Parser.repeat(count, PARSE_LIMIT, f, ...)` """
        return self.repeat(count, self.PARSE_LIMIT, f, *args, **kwargs)
    def at_least_ic(self, count: int, f, *args, **kwargs):
        """ Alias for `Parser.repeat(count, PARSE_LIMIT, f, ..., ic=True)` """
        return self.repeat(count, self.PARSE_LIMIT, f, *args, **kwargs, ic=True)
    def at_most(self, count: int, f, *args, **kwargs):
        """ Alias for `Parser.repeat(0, count, f, ...)` """
        return self.repeat(0, count, f, *args, **kwargs)
    def at_most_ic(self, count: int, f, *args, **kwargs):
        """ Alias for `Parser.repeat(0, count, f, ..., ic=True)` """
        return self.repeat(0, count, f, *args, **kwargs, ic=True)
    def exactly(self, count: int, f, *args, **kwargs):
        """ Alias for `Parser.repeat(count, count, f, ...)` """
        return self.repeat(count, count, f, *args, **kwargs)
    def exactly_ic(self, count: int, f, *args, **kwargs):
        """ Alias for `Parser.repeat(count, count, f, ..., ic=True)` """
        return self.repeat(count, count, f, *args, **kwargs, ic=True)

    x1   = one
    x1_  = one_or_more
    x0_  = zero_or_more
    x0_1 = zero_or_one

    def __getattr__(self, name):
        # Dynamic quantifiers:
        # - xK           -> exactly K, x1, x2i,
        # - xK_M         -> between K and M inclusive x0_2i
        # - xK_          -> K or more x2_,  x2_i
        # - two          -> exactly 2, three, three_ic
        # - two_to_five  -> between 2 and 5, two_to_five_ic
        # - two_to_5     -> between 2 and 5, two_to_5_ic
        # - four_or_more -> 4 or more, four_or_more_ic
        # while two_or_five is illegal 'one_to_more' is allowed and means 1 or more
        # suffixes: i for short form, _ic are for long forms
        # ic = ignore case
        cls = self.__class__
        def set_meth(x_):
            x_.__name__ = name;  x_.__qualname__ = f"{cls.__name__}.{name}"
            setattr(cls, name, x_)  # cache under the original requested name (e.g., 'one_ic')
            return getattr(self, name)
        base = name
        short = base.startswith('x')
        if (has_ic := (short and name.endswith('i')) or (not short and name.endswith('_ic'))):
            base = base[:-1] if short else base[:-3]
            if base in ('one', 'one_or_more', 'zero_or_more', 'zero_or_one', 'x1', 'x1_', 'x0_', 'x0_1'):
                meth = getattr(self.__class__, base)
                def x_ic(self, f, *args, **kwargs):  return meth(self, f, *args, **kwargs, ic=True)
                return set_meth(x_ic)
        lower, upper = None, cls.PARSE_LIMIT
        if short:
            lo_s, *up_s = base[1:].split('_', 1)
            if lo_s.isdigit():
                lower = int(lo_s)
            if not up_s: # xK exactly, e.g., x2
                upper = lower
            elif up_s := up_s[0]:
                if not up_s.isdigit():
                    raise AttributeError(f"{cls.__name__!s} has no attribute {name!r}")
                upper = int(up_s)
        else:  # spelled patterns, e.g., "two", "two_to_five", "two_to_5", "four_or_more"
            lo_s, *up_s = (base[:-8], 'more') if base.endswith('_or_more') else base.split('_to_', 1)
            lower = cls.NUM_WORDS.get(lo_s)
            if not up_s: # exactly K, e.g., "two"
                upper = lower
            elif (up_s := up_s[0]).isdigit(): # K_to_M, e.g., "two_to_5" or "two_to_five"
                upper = int(up_s)
            elif up_s != 'more' and (upper := cls.NUM_WORDS.get(up_s)) is None: # K_or_cardinal, e.g., "two_to_five"
                raise AttributeError(f"{cls.__name__!s} has no attribute {name!r}")
        if lower is None or upper < lower:
            raise AttributeError(f"{cls.__name__!s} has no attribute {name!r}")

        if has_ic:
            def x_(self, f, *args, **kwargs):  return self.repeat(lower, upper, f, *args, **kwargs, ic=True)
        else:
            def x_(self, f, *args, **kwargs):  return self.repeat(lower, upper, f, *args, **kwargs)
        return set_meth(x_)

    def _match_any(self, t):
        prev_len = None
        for k in t:
            if (key_len := len(k := str(k))) != prev_len: # cache the slice
                slc = self.slice(key_len)
            if slc == k: # pylint: disable=possibly-used-before-assignment
                return k
            prev_len = key_len
        return None
    def _match_any_ic(self, t):
        prev_len = None
        for k in t:
            if (key_len := len(k := str(k))) != prev_len: # cache the slice
                slc = self.slice(key_len).lower()
            if slc == k.lower(): # pylint: disable=possibly-used-before-assignment
                return k
            prev_len = key_len
        return None
    def _match_more(self, ctx):
        k = 0
        while self.lookahead.one_with_ctx(ctx).is_active:
            self.commit # pylint: disable=pointless-statement
            k += 1
            if k > Parser.PARSE_LIMIT:  raise ValueError("Infinite loop or input too long")
        return self.backtrack(), k

    def _dispatch_one(self, f, kwargs):
        neg, f = Not.crack(f)

        if callable(f):
            if hasattr(f, '__parsek_sub'): # needs args
                if hasattr(f, '__parsek_new_stack'):
                    f_ = self._one_sr_ns_neg if neg else self._one_sr_ns
                else:
                    f_ = self._one_sr_neg if neg else self._one_sr
                return (lambda args, kwargs, f=f_, sr=f: f(sr, args, kwargs)), True
            if is_unary(f):
                if kwargs.get('ic', False):
                    f_ = self._one_unary_neg_ic if neg else self._one_unary_ic
                else:
                    f_ = self._one_unary_neg if neg else self._one_unary
                return (lambda f=f_, pred=f: f(pred)), False
            # Non-unary single-char callable matcher that needs args/kwargs:
            if kwargs.get('ic', False):
                f_ = self._one_call_neg_ic if neg else self._one_call_ic
            else:
                f_ = self._one_call_neg if neg else self._one_call
            return (lambda args, kwargs, f=f_, cl=f: f(cl, args, kwargs)), True

        if isinstance(f, tuple) and not all(isinstance(x, (str, Val)) for x in f):
            return (lambda args, kwargs, f=self._one_multi_neg if neg else self._one_multi, t=f: f(t, args, kwargs)), True
        if isinstance(f, (tuple,set,list,Mapping)):
            assert all(isinstance(x, (str, Val)) for x in f), "Match set elements must be str or Val"
            matcher = self._match_any_ic if kwargs.get('ic', False) else self._match_any
            f_ = self._one_map_neg if neg else self._one_map
            if isinstance(f, Mapping):
                return (lambda args, _kwargs, f=f_, m=f, matcher=matcher: f(m, matcher, args)), True
            return (lambda f=f_, t=f, matcher=matcher: f(t, matcher, None)), False

        # literal:
        if not isinstance(f, str):  f = str(f)
        if (ic := kwargs.get('ic', False)):
            f = f.lower()
        if (f_len := len(f)) == 1: # single char
            if ic:  f_ = self._one_char_neg_ic if neg else self._one_char_ic
            else:   f_ = self._one_char_neg    if neg else self._one_char
            return (lambda f=f_, ch=f: f(ch)), False
        if f_len == 0: # empty string one(Not('')) consumes one char, even END_CHAR unlike one(Not(p.END_CHAR))
            return ((lambda: True) if not neg else self.next), False
        # str match n > 1
        if ic:  f_ = self._one_str_neg_ic if neg else self._one_str_ic
        else:   f_ = self._one_str_neg    if neg else self._one_str
        return (lambda f=f_, s=f, l=f_len: f(s, l)), False

    _dispatch = _dispatch_one # non-tracing dispatch function

    def _one_sr(self, f, args, kwargs):
        return bool(f(self, *args, **kwargs))
    def _one_sr_neg(self, f, args, kwargs):
        if advance := not bool(f(self._fork(), *args, **kwargs)): self.next()
        return advance
    def _one_sr_ns(self, f, args, kwargs):
        # NOTE: While we can easily backtrack on failure here, by simply not calling _join():
        #   `if advance := bool(f(p := self._fork(), *args, **kwargs)): self._join(p)`
        # We join for success and failures. This is so we can stay consistent with all other `one(...)` methods
        # and leave the parser at the position of failure.
        advance = bool(f(p := self._fork(), *args, **kwargs));  self._join(p)
        return advance
    def _one_sr_ns_neg(self, f, args, kwargs):
        if advance := not bool(f(self._fork(), *args, **kwargs)): self.next()
        return advance

    def _one_unary(self, f):
        if advance := bool(f(self.ch)): self.next()
        return advance
    def _one_unary_ic(self, f):
        if advance := bool(f(self.ch.lower())): self.next()
        return advance
    def _one_unary_neg(self, f):
        if advance := not bool(f(self.ch)): self.next()
        return advance
    def _one_unary_neg_ic(self, f):
        if advance := not bool(f(self.ch.lower())): self.next()
        return advance

    def _one_call(self, f, args, kwargs):
        if advance := bool(f(self.ch, *args, **kwargs)): self.next()
        return advance
    def _one_call_ic(self, f, args, kwargs):
        if advance := bool(f(self.ch.lower(), *args, **kwargs)): self.next()
        return advance
    def _one_call_neg(self, f, args, kwargs):
        if advance := not bool(f(self.ch, *args, **kwargs)): self.next()
        return advance
    def _one_call_neg_ic(self, f, args, kwargs):
        if advance := not bool(f(self.ch.lower(), *args, **kwargs)): self.next()
        return advance

    def _one_multi(self, t, args, kwargs):
        last_i = len(t) - 1
        for i, x in enumerate(t):
            if self.lookahead.one(x, *args, **kwargs):
                return self.commit.is_ok
            if i < last_i: # backtrack if not the last one
                self.backtrack()
            else: # commit the last one, since we failed to match any
                self.commit # pylint: disable=pointless-statement
        return False
    def _one_multi_neg(self, t, args, kwargs):
        for x in t:
            if self.lookahead.one(x, *args, **kwargs):
                self.backtrack()
                return False
            self.backtrack()
        self.next()
        return True

    def _one_map(self, m, matcher, args):
        if advance := (key := matcher(m)) is not None:
            self.next(len(key))
            if args: self.accumulate(Acc(*args), m[key])
        return advance
    def _one_map_neg(self, m, matcher, _args):
        if advance := matcher(m) is None: self.next()
        return advance

    def _one_char(self, ch):
        if advance := ch == self.ch: self.next()
        return advance
    def _one_char_ic(self, ch):
        if advance := ch == self.ch.lower(): self.next()
        return advance
    def _one_char_neg(self, ch):
        if advance := ch != self.ch: self.next()
        return advance
    def _one_char_neg_ic(self, ch):
        if advance := ch != self.ch.lower(): self.next()
        return advance

    def _one_str(self, s, s_len):
        if advance := self.slice(s_len) == s: self.next(s_len)
        return advance
    def _one_str_ic(self, s, s_len):
        if advance := self.slice(s_len).lower() == s: self.next(s_len)
        return advance
    def _one_str_neg(self, s, s_len):
        if advance := self.slice(s_len) != s: self.next()
        return advance
    def _one_str_neg_ic(self, s, s_len):
        if advance := self.slice(s_len).lower() != s: self.next()
        return advance

    @staticmethod
    def _make_chars_matcher(spec: str):
        @parser_subroutine
        def char(p, out, esc = None):
            return p.if_.one('\\').one(p.NOT_END_CHAR, out, esc).else_.one(p.NOT_END_CHAR, out).endif
        @parser_subroutine
        def range_(p, left, out):
            return p.one('-').one(char, e := Val()).do(lambda: out.append(Range(left, e.v)))
        @parser_subroutine
        def atom(p, s, r):
            return (p.one(char, left := Val(), esc := Val(False)).
                    if_.one(range_, left.v, r).
                    else_.do(lambda: s.append(p.END_CHAR) if (p.ch == p.END_CHAR and left == '$' and not esc)
                                    else s.append(left.v)).endif)
        if __debug__:
            with Parser._no_trace():
                Parser(spec).x0_1('^', neg := Val(False)).x0_(atom, chars:=[], ranges := [])
        else:
            Parser(spec).x0_1('^', neg := Val(False)).x0_(atom, chars:=[], ranges := [])

        out, r_chars = [], []
        for r in ranges:
            if len(r) <= 64: # `ch in "abc"` is faster than `'a' <= ch <= 'c'` for ranges under ~1K chars
                r_chars.extend(chr(c) for c in range(ord(r.lo), ord(r.hi)+1))
            else:
                out.append(r)
        if chars or r_chars: # append to the end, this way the end_char (if any) is always last
            s = ''.join(dict.fromkeys(r_chars + chars)) # remove duplicates, keep order
            out.append(In(s) if len(s) > 1 else s)
        out = tuple(out) if len(out) > 1 else out[0] if out else ''
        return Not(out) if neg else out

    @staticmethod
    def chars(s: str):
        """Returns a matcher for the specified character class (like RE specs but without enclosing `[ ]`)

        Args:
            s: character class specifications. You can have multiple ranges and plain characters in
            any order. They will be deduplicated and optimized for matching.
                - Leading '^' negates the class.
                - Trailing '$' adds END_CHAR to the class.
                - Ranges 'a-z' (inclusive). If reversed (z-a), gets normalized.
                - Escape characters with backslash `\\` as needed.
                - Literal '-' if first/last, between two ranges, or escaped.

        Returns:
            matcher, directly from the cache, do not modify it, treat it as an opaque immutable
            value to pass to quantifiers like one(), one_or_more(), etc.
            **Note:** Even though chars() is cached, when performance is critical, cache the result locally in a variable.

        Examples:
        ```python
            p.one(p.chars('abc'))          # matches 'a' or 'b' or 'c'
            p.one(p.chars('a-z'))          # matches any lowercase letter
            p.one(p.chars('a-zA-Z0-9'))    # matches any letter or digit
            p.one(p.chars('^a-z0-9_'))     # matches anything _except_ letters, digits, or underscore
            p.one(p.chars('^\\n$'))         # matches anything _except_ newline or end of input
        """
        if (found := Parser._cache_chars.get(s)) is not None:
            return found
        Parser._cache_chars[s] = (r := Parser._make_chars_matcher(s))
        return r

    @staticmethod
    def accumulate(out, v):
        """Accumulates value `v` into `out` target. The `out` parameter is a flexible "sink" that
        can be any of the following:
        1. Object with an `append` or 'add' method:
           - `Val` instance (calls `Val.append(v)`)
           - `list` (`list.append(v)`)
           - `set` (`set.add(v)`)
           - Any custom object exposing `append(v)` or `add(v)` method.
        2. `Acc`: each contained element (which may itself be a `Acc` or any other accepted target) is processed recursively.
        3. Empty tuple () -> ignored (no-op).
        4. Tuple where the first element is a `Val`: treated as a collection of `out` targets; each element processed recursively.
        5. Mapping accumulator tuple: `(mapping, key [, converter_or_combiner])`
           - `mapping`: dict-like with get / item assignment.
           - `key`: mapping key to store/accumulate into.
           - Optional third element:
              * If callable accepting ONE positional argument (unary): treated as a converter; `v = fn(v)` before combining.
              * Otherwise (or if the unary attempt raises TypeError): treated as a combiner with signature `combiner(old_value, new_value) -> combined_value`.
           - Combination rule when no combiner supplied uses `default_combiner(old, new)`:
              * If old is `None` -> adopt new.
              * If old has `append` -> `old.append(new)` and old container is returned (in-place append).
              * If new is `bool` -> `(old or new)`.
              * Else -> `old + new`.
        6.  Mapping, then the value `v` should be one of:
            - (key, value) -> combine with `default_combiner` and add to `out` mapping
            - (key, value, converter_or_combiner) -> use the same logic as in (5.) above.
            - {k: v, ...} or any Mapping -> merged key-wise using default_combiner
        7. Callable: invoked as out(v) for arbitrary side-effects, emitting, or storage.

        Examples:
        ```python
            r = Val('')
            Parser.accumulate(r, 'abc')               # r.v -> 'abc'
            Parser.accumulate(r, 'def')               # r.v -> 'abcdef'

            d = {}
            Parser.accumulate((d, 'id', int), '42')   # d['id'] -> 42
            Parser.accumulate((d, 'id', int), '1')    # d['id'] -> 43

            Parser.accumulate(d, ('name', 'Alice'))   # d['name'] -> 'Alice'

            d2 = {}
            Parser.accumulate((d2, 'count', lambda old, new: (old or 0) + 1), 'x')  # d2['count'] == 1
            Parser.accumulate((d2, 'count', lambda old, new: (old or 0) + 1), 'y')  # d2['count'] == 2

            Parser.accumulate((r1 := Val(), r2 := Val()), 'val')  # both r1.v and r2.v get 'val'
        ```
        """
        if (append_ := getattr(out, 'append', None) or getattr(out, 'add', None)):
            append_(v)
        elif out is None:
            pass # ignore None out
        elif isinstance(out, Acc):
            for r in out:
                Parser.accumulate(r, v) # `r` might NOT be of Val type so we recurse
        elif isinstance(out, tuple):
            if len(out) == 0:
                return # empty tuple, ignore
            if isinstance(out[0], Val):  #all(isinstance(r, Val) for r in result):
                for r in out:
                    Parser.accumulate(r, v) # some `r` might NOT be of Val type so we recurse
            else: # Dict setting/appending when we get a tuple (dict, key, [converter/combiner])
                dict_append(out, v)
        elif isinstance(out, Mapping): # we support dict appends when the v is a tuple: (key, v)
            dict_update(out, v)
        else:
            try:
                out(v) # try accumulate result as a callable
            except Exception as e:
                raise ValueError(f"Accumulation failed while calling {out!r}({v!r})") from e



    # Utility subroutines for parsing common literals and structures: ints, strings, lists, dicts
    @staticmethod
    @parser_subroutine
    def identifier(p: 'Parser', out=None, **_kwargs) -> bool:
        """Parse an identifier: starts with a letter or underscore, followed by letters, digits, or underscores.
        More technically: `{XID_START}{XID_CONTINUE}*`."""
        def xid_continue(ch):  return str.isidentifier(ch) or str.isdigit(ch)

        pos = p.pos
        if p.one(str.isidentifier).zero_or_more(xid_continue):
            Parser.accumulate(out, rv := p.slice_from(pos))
            if __debug__:
                if p.tracing: p.trace(2, f"{Parser._f_name(Parser.identifier)} +->{rv!r}")
            return True
        return False

    @staticmethod
    @parser_subroutine
    @add_static('sign__', In('+-'))
    def decimal(p: 'Parser', out=None, **_kwargs) -> bool:
        """Parse a decimal number, integer or float. Python-style ints and floats are supported,
        including optional exponent part. Ints are returned as int, floats as float.

        Returns `False` if no match (no backtracking).
        Use with lookahead if you also want to backtrack on no match,
        otherwise the parser will be advanced to the point of failure.
        e.g.: `p.if_.one(p.decimal, r).endif` will backtrack if no decimal found.
        """
        sign = Parser.decimal.sign__
        is_digit = str.isdigit
        is_float = Val(False)
        ok = Val(False)
        pos = p.pos
        if (p.x0_1(sign).x0_(is_digit, ok).x0_1('.', is_float).x0_(is_digit, ok).fail_if(Not(ok)).
            if_.x0_1('e', ok.clear, ic=True).x0_1(sign).x1_(is_digit, ok, is_float).endif) and ok:
            rv_s = p.slice_from(pos)
            Parser.accumulate(out, rv := float(rv_s) if is_float else int(rv_s))
            if __debug__:
                if p.tracing: p.trace(2, f"{Parser._f_name(Parser.decimal)} +->{rv}")
            return True
        return False

    @staticmethod
    @parser_subroutine
    def int_(p: 'Parser', out=None, **_kwargs) -> bool:
        """Parse a base 10 integer. Negative numbers are supported.

        Use with lookahead if you also want to backtrack on no match,
        otherwise the parser will be advanced to the point of failure"""
        pos = p.pos
        if p.zero_or_one(('-','+')).one_or_more(str.isdigit):
            Parser.accumulate(out, rv := int(p.slice_from(pos)))
            if __debug__:
                if p.tracing: p.trace(2, f"{Parser._f_name(Parser.int_)} +->{rv}")
            return True
        return False

    @staticmethod
    @parser_subroutine
    def uint(p: 'Parser', out=None, **_kwargs) -> bool:
        """Parse a base 10 unsigned integer.

        Use with lookahead if you also want to backtrack on no match,
        otherwise the parser will be advanced to the point of failure"""
        pos = p.pos
        if p.zero_or_one('+').one_or_more(str.isdigit).is_ok:
            Parser.accumulate(out, rv := int(p.slice_from(pos)))
            if __debug__:
                if p.tracing: p.trace(2, f"{Parser._f_name(Parser.uint)} +->{rv}")
            return True
        return False

    @staticmethod
    @parser_subroutine_new_stack
    @add_static('State__', Enum('State', ['OPENER', 'AFTER_OPENER', 'ITEMS', 'AFTER_VALUE']))
    @add_static('brackets__', {'[':']'})
    @add_static('tms__', lambda p, ch, term: bool(p.next()) if ch == term else False)
    @add_static('tmm__', lambda p, _ch, ctx: p.if_.one_with_ctx(ctx).else_.fail.endif.is_ok)
    @add_static('set_tm__', lambda p, t: ((p.collection.tms__, t) if isinstance(t, str) and len(t) == 1
                                          else (p.collection.tmm__, p.get_one_ctx(t))))
    @add_static('ws__', lambda _: False)
    def collection(p: 'Parser', item_parser, out=None, *,
                   sep: str | tuple = ',', brackets: Mapping[str, str] = None, empty_item: callable = None,
                   on_err: callable = err, ws = str.isspace, **kwargs) -> bool:
        """Parse a delimited collection (lists, dicts, tuples, etc.) with optional brackets,
        separators, recursion, and empty-item handling.

        By default, parses Python-style lists, e.g. `"[a, b, c]"`.
        Whitespace (excluding before/after opening and closing brackets) is handled automatically.

        Args:
            p (Parser): The parser instance.
            item_parser (callable): Parser subroutine for individual items. Must be callable as
                `item_parser(p, out, sep=sep, term=terminator, **kwargs)`.
                The separator and terminator are passed (as keyword args) in case the item parser needs to know them
                (e.g., to stop parsing on them).
                **Important:** item_parser must not consume the separator or terminator, this is handled by
                `collection()`. `item_parser` can be recursive, to parse nested lists/dicts (see example below).
            out (Any): Container/sink to receive parsed items. Can be any object(s) that Parser.accumulate() supports.
            sep (str | tuple, default=`','`): One or more separator characters, e.g. `';'` or a tuple `(';', ',')`.
            brackets (dict, default=`{'[':']'}`): Opening and closing brackets for the collection. Multiple pairs
                allowed, e.g., `{'[':']', '{':'}'}`. If the opener was already matched, pass `{None: ']'}` where
                ']' should be the expected closing bracket. For unbracketed collections, use `{None: p.END_CHAR}`.
                Closing bracket can be any matcher suitable for Parser.one() to match the closing bracket. Opening
                brackets must always be a single character or None when you open the collection yourself.
            empty_item (callable): Controls how empty entries (e.g. `[a,,b,]`) are handled.
                - None (default) → empty items are ignored/skipped.
                - callable() → use return value as the value for the empty item.
                    To use `None` for empty items, pass in `empty_item=type(None)` or `empty_item=lambda: None`.
                    To use empty strings pass `empty_item=str`. For dicts, empty items are best ignored or you
                    can raise an error in the empty_item callable. You can also have empty_item return a (key, value)
                    tuple to add to the dict. See Parser.accumulate() for details.
                - callable(is_last: bool) → if callable accepts a single boolean argument, it will be called with
                    `is_last=True` for trailing empty items and `is_last=False` for non-trailing empty items.
                    This allows you to handle trailing empty items differently if needed. For example,
                    `(lambda is_last=False: '' if not is_last else ...)`, will return an empty string for
                    non-trailing empty items, and `...` (Ellipsis) to append nothing for the trailing empty item.

            on_err (callable(p, msg) | callable(msg)): If not None, called on any parsing errors (after the opening
                bracket). Default: `Parser.err` which raises ValueError.
            ws (callable): If not None, called to skip whitespace between items and separators. The default is
                `str.isspace`.
            **kwargs: Forwarded unchanged to `item_parser`.

        Returns:
            bool: `True` if collection parsed successfully. `False` if no opening
            bracket was found, or if a parsing error occurred after `on_err` is called (if it doesn't raise).

        Examples:
        Parse a list of integers:
        ```python
        p = Parser(' [1, 2, 3] <- a list')
        lst = []
        p.one(p.collection, p.int_, lst)
        assert lst == [1, 2, 3]
        ```

        Recursive `item_parser` for deeply nested list of booleans, numbers, strings, and lists:
        ```python
        p = Parser(' " [ 1, 'abc' , 2.6, True, [3, 4, 'def'], 5] " <- a nested list')
        lst = []
        @p.subroutine # Define item parser to handle booleans, numbers, strings, and nested lists of the same
        def item_(p: Parser, out, **_kwargs):
            return (p.if_.one(p.decimal, out).   # try number
                      elif_.one(p.string, out).  # try string
                      # try bool, ignore-case:
                      elif_.one(('true', 'false'), lambda v: out.append(v.lower() == 'true'), ic=True).
                      else_.one(p.collection, item_, nested_l := []).do(out.append, nested_l). # must be a nested list
                      endif)

        p.ws.one(p.collection, item_, lst)
        assert lst == [1, 'abc', 2.6, True, [3, 4, 'def'], 5]
        ```

        Parsing a dict of ints:
        ```python
        p = Parser(' { a: 1, b: 2, c: 3 } <- a dict')
        d = {}
        @p.subroutine
        def item_(p: Parser, out, **_kwargs):
            return p.one(str.isalpha, k := p.Val()).ws.one(':').ws.one(p.decimal, (out, k))

        p.ws.one(p.collection, item_, d, brackets={'{': '}'})
        assert d == {'a': 1, 'b': 2, 'c': 3}
        ```
        **NOTE:** The `Parser.collection()` as well as `Parser.string()` subroutines use a *Finite State Machine (FSM)*
        to parse and are good examples of how to implement FSM-based subroutines which Parsek supports natively.
        """
        State    = Parser.collection.State__ # pylint: disable=invalid-name
        set_tm   = Parser.collection.set_tm__
        brackets = brackets or Parser.collection.brackets__
        ws       = ws or Parser.collection.ws__
        sep      = sep if isinstance(sep, tuple) else (sep,)
        is_open  = None in brackets # collection is already opened?
        empty_args_f = None # cache the args tuple for empty_item()
        term_m, term = set_tm(p, brackets[None]) if is_open else (None, None)

        if __debug__:
            if tracer := (p.trace if p.tracing else None):
                dbg_count = 0 # count items for the debug trace
                dbg_name = Parser._f_name(Parser.collection)

        p.goto(State.AFTER_OPENER if is_open else State.OPENER)
        while not p.is_past_end:
            ch = p.ch
            match p.state:
                case State.OPENER:
                    if ch in brackets:
                        term_m, term = set_tm(p, brackets[ch])
                        p.goto(State.AFTER_OPENER)
                        if __debug__:
                            if tracer: tracer(2, f"{ch!r} --> {dbg_name} --> opened --> True")
                    else:
                        if __debug__:
                            if tracer: tracer(4, f"{ch!r} --> {dbg_name} --> False")
                        return False
                case State.AFTER_OPENER:
                    if term_m(p, ch, term):
                        if __debug__:
                            if tracer: tracer(2, f"{ch!r} --> {dbg_name} --> closed (empty collection) --> True")
                        return True
                    if ch == p.END_CHAR:
                        return p.on_err(on_err, "Unclosed collection")
                    if not ws(ch):
                        p.skip_to(State.ITEMS)
                case State.ITEMS:
                    if ch in sep:
                        if __debug__:
                            if tracer: tracer(3, f"{ch!r} --> {dbg_name} --> (no item) separator --> True")
                        if empty_item is not None:# pragma: no branch; NOTE: coverage bug, thinks branch is always True
                            if empty_args_f is None: # cache the args tuple
                                empty_args_f = (False,) if is_unary(empty_item) else ()
                            if (ei := empty_item(*empty_args_f)) is not ...: # Ellipsis means append nothing
                                p.accumulate(out, ei)
                            if __debug__:
                                if tracer: dbg_count += 1
                    elif term_m(p, ch, term):
                        if empty_item is not None: # This is the last EMPTY item before closing: `[a,b,c, ]`
                            empty_args_t = (True,) if is_unary(empty_item) else ()
                            if (ei := empty_item(*empty_args_t)) is not ...: # Ellipsis means append nothing
                                p.accumulate(out, ei)
                            if __debug__:
                                if tracer: dbg_count += 1
                        if __debug__:
                            if tracer: tracer(2, f"{ch!r} --> {dbg_name} --> closed ({Parser._units(dbg_count, 'item')}) --> True")
                        return True
                    elif ws(ch):
                        pass # ignore
                    elif ch == p.END_CHAR:
                        return p.on_err(on_err, "Unclosed collection")
                    elif p.one(item_parser, out, sep=sep, term=term, **kwargs):
                        if __debug__:
                            if tracer: dbg_count += 1
                        p.skip_to(State.AFTER_VALUE)
                    else:
                        return p.on_err(on_err, "Unexpected input for collection")
                case _: # State.AFTER_VALUE:
                    if ch in sep:
                        if __debug__:
                            if tracer: tracer(3, f"{ch!r} --> {dbg_name} --> separator --> True")
                        p.goto(State.ITEMS)
                    elif term_m(p, ch, term):
                        if __debug__:
                            if tracer: tracer(2, f"{ch!r} --> {dbg_name} --> closed ({Parser._units(dbg_count, 'item')}) --> True")
                        return True
                    elif not ws(ch):
                        p.skip_to(State.ITEMS)
            p.next()
        if __debug__:
            if tracer: tracer(4, f"{p.END_CHAR!r} --> {dbg_name} --> False")
        return False

    @staticmethod
    @parser_subroutine_new_stack
    @add_static('esc__', {'\\' : '\\', '"': '"', "'":"'", 'a': '\a', 'b': '\b', 'f': '\f', 'n': '\n', 'r': '\r',
                          't': '\t', 'v': '\v', 'x': 2, 'u': 4, 'U': 8, '0': None, '1': None, '2': None, '3': None,
                          '4': None, '5': None, '6': None, '7': None})
    @add_static('quotes__', {'"': '"', "'": "'"})
    @add_static('hex_count__', {'x':2, 'u':4, 'U':8})
    @add_static('empty__', {})
    @add_static('State__', Enum('State', ['INITIAL', 'INSIDE', 'ESCAPE']))
    def string(p: 'Parser', out=None, *, escapes = None, quotes=None, replace=None, on_err=err, **_kwargs) -> bool:
        """ Subroutine to parse a quoted string with support for escape sequences and on the fly replacements.

        Default args are set to parse standard Python-style double or single quoted strings with standard escapes.
        Args:
            p (Parser): The parser instance.
            out (Any): The container/sink to append the parsed string to. This can be any object(s) that
                Parser.accumulate() supports.
            escapes (dict): Additional escape sequences to support, e.g., `{'S': '😀'}`. Default: None.
                Standard Python string literal escapes are still processed: `\\n, \\r, \\", \\', \\\\, \\ue000`, etc.,
                unless you use `Raw({...})` to disable and replace them with the new set. Pass in `Raw(None)` to have
                exactly the Python's raw-string behavior.
            quotes (dict): The opening and closing quote characters. Default: `{'"': '"', "'": "'"}`. This can be any
                pair of single-character strings. For example, `{'«': '»', '<': '>'}`. If the opening quote was already
                matched, pass in `{None: '"'}` where `'"'` should be the expected closing quote.
                Closing quote can be any matcher suitable for Parser.one() to match the closing quote. Opening
                quotes must always be a single character or None when you open the string yourself.
            replace (dict): Per character replacement mapping {char: replacement_str}. Default: None. For example,
                `{'$': 'USD'}`. and if you need to be able to escape the replacement char, `escapes={'$': '$'}`.
                So `'5$ and 10\\$'` --> `'5USD and 10$'`.
            on_err (callable(p, msg)): If not None, called on any parsing errors (after the opening quote).
                Default: Parser.err which raises ValueError.
            kwargs: Additional keyword arguments which are ignored.

        Returns:
            bool: `True` if string parsed successfully. If there's no opening quote `on_err` is *NOT* called and
            `False` is returned. If there's a parsing error after the opening quote, `on_err` *IS* called, which
            by default raises ValueError, and `False` is returned (if no exception).

        **NOTE:** The `Parser.collection()` as well as `Parser.string()` subroutines use a *Finite State Machine (FSM)*
        to parse and are good examples of how to implement FSM-based subroutines which Parsek supports natively.
        """
        State    = Parser.string.State__ # pylint: disable=invalid-name
        set_tm   = Parser.collection.set_tm__
        override, escapes = Raw.crack(escapes)
        escapes  = escapes or Parser.string.empty__
        escapes_ = escapes if override else Parser.string.esc__
        if override: escapes = Parser.string.empty__ # escapes are in escapes_ now
        quotes   = quotes or Parser.string.quotes__
        replace  = replace or Parser.string.empty__
        term_m, term = set_tm(p, quotes[None]) if (is_open := None in quotes) else (None, None)

        if __debug__:
            if tracer := (p.trace if p.tracing else None):
                dbg_name = Parser._f_name(Parser.string)

        s = [] # output string accumulator
        p.goto(State.INSIDE if is_open else State.INITIAL)
        while not p.is_past_end:
            ch = p.ch
            match p.state:
                case State.INITIAL:
                    if ch in quotes:
                        term_m, term = set_tm(p, quotes[ch])
                        p.goto(State.INSIDE)
                    else:
                        if __debug__:
                            if tracer: tracer(4, f"{ch!r} --> {dbg_name} --> False")
                        return False
                case State.INSIDE:
                    if ch == '\\': # escape
                        p.goto(State.ESCAPE)
                    elif ch in replace:
                        s += replace[ch]
                    elif term_m(p, ch, term):
                        if __debug__:
                            if tracer:
                                tracer(3, f"{ch!r} --> {dbg_name} --> True")
                                tracer(2, f"{dbg_name} +->{str_concise(''.join(s), 25, True)!r}")
                        Parser.accumulate(out, ''.join(s))
                        return True
                    elif ch == Parser.END_CHAR:
                        return p.on_err(on_err, "String must end with a matching quote")
                    else:
                        s += ch
                case _: # State.ESCAPE: # Escape sequence: \n, \r, \", \\, ...
                    if ch in escapes_:
                        if isinstance(ch_esc := escapes_[ch], str): # regular escapes:
                            s += escapes_[ch]
                            p.goto(State.INSIDE)
                        elif ch_esc is None: # octal, first digit is ch
                            p.one_to_three(In('01234567'), acc=(digits := Val()))
                            s += chr(int(digits.v, 8))
                            p.skip_to(State.INSIDE)
                        else: # hex escapes
                            assert ch_esc in (2, 4, 8), "hex escape count must be 2, 4, or 8"
                            if (p.next().exactly(ch_esc, In('01234567890abcdef'),
                                                acc=(digits := Val()), ic=True)):
                                s += chr(int(digits.v, 16))
                            else:
                                return p.on_err(on_err, f"Invalid escape sequence, expected exactly {ch_esc} hex digits after \\{ch}")
                            p.skip_to(State.INSIDE)
                    elif not escapes_: # raw format:
                        s += '\\'; s += ch
                        p.goto(State.INSIDE)
                    else:
                        try:
                            s += escapes[ch]
                        except KeyError:
                            return p.on_err(on_err, f"Unexpected string escape sequence \\{ch}")
                        p.goto(State.INSIDE)
            if __debug__:
                if tracer: tracer(3, f"{ch!r} --> {dbg_name} --> True")
            p.next()
        if __debug__:
            if tracer: tracer(4, f"{p.END_CHAR!r} --> {dbg_name} --> False")
        return False

    def on_err(self, f, msg: str):
        """ Called on parsing errors by routines that provide error handling."""
        if f: # this is a callable(parser, msg), e.g., Parser.err()
            if isinstance(bound_p := getattr(f, '__self__', None), Parser): # bound method, probably Parser.err
                if bound_p is self:
                    f(msg) # don't pass the parser, just call it
                else: # different parser instance, get underlying function and call with our parser
                    getattr(f, '__func__', f)(self, msg)
            elif is_unary(f):
                f(msg)
            else:
                f(self, msg)
        return False


    #=== TRACING ======================================================================================================
    @classmethod
    def set_trace(cls, level: int = 3, color: bool = True, out: callable = print):
        """Enable/disable tracing for all Parser instances. Only has effect in debug mode (i.e. `__debug__ is True`).

        *Note:* tracing is expensive, use it only to debug your parser routines. It is always disabled by default.
        Args:
            level (int): Trace level, 0=off, 1=minimal, 5=maximal. Default is 3.
            color (bool): If True, enables colored output (ANSI escape codes). Default is True.
            out (callable): The output function to use, default is print(). The `out` function must accept a single
                string argument.

        Returns:
            tuple: Previous trace settings as (level:int, color:bool, out:callable) or (0, True, print).

        Use `Parser.trace()` to output your own trace messages from custom parser routines.
        """
        if __debug__: # pylint: disable=no-else-return
            r = cls._trace if cls._trace else (0, True, print)
            if level <= 0: # disable tracing
                cls._trace = None
                cls._dispatch = cls._dispatch_one
            else:
                cls._trace = (int(min(5, level)), bool(color), out)
                cls._dispatch = cls._dispatch_one_with_trace
                if cls._tracer is None:
                    cls._tracer = cls._Tracer(cls)
            return r # return previous settings
        else: # NOTE: keep this else so it will be promoted in minify.py
            return (0, True, print) # tracing not available in optimized mode

    def trace(self, level, msg):
        """Outputs a trace message if `__debug__` and tracing is enabled.

        The trace message is indented according to the current lookahead stack depth and colorized. Returns self,
        allowing chaining.
        Args:
            level (int): Trace level, 0=off, 1=minimal, 5=maximal.
            msg (str | callable): The message to output. If a callable (nullary), it will be called to get the
                message. This is useful to avoid the overhead of formatting the message

        **Note:** tracing is expensive! Use it only to debug your parser routines. Stack inspection is required to
        print the stack chain (using `inspect` module). Then inspecting the messages for keywords to colorize them.
        It is only available in debug mode (when Python is not run with -O optimization flag) and only if tracing
        is enabled with `Parser.set_trace()`. We replace parser methods that need tracing with tracing versions only
        when tracing is enabled, so when tracing is disabled there is virtually no overhead. With -O optimization,
        there is no overhead at all. In custom parser routines we write for other projects we use two guards at all
        trace() call sites to minimize the overhead of tracing:
        ```python
        if __debug__: # if in this exact form `python -O` will remove the entire block
            if parser.tracing: parser.trace(2, f"some message {value}")
            # the second guard avoids the overhead of the call and
            # of the formatting of the f-string when tracing is disabled
        ```
        You can use the same approach as above or at least use a lambda if your f-string is complex:
        ```python
        parser.trace(2, lambda: f"complex message {heavy.value}") # message formatting deferred until needed
        ```
        For a quick debugging message put a `trace()` call in your chain expressions (it will be a no-op if tracing
        is disabled):
        ```python
        p.if_.one('hello').trace(3, "--> found hello").else_.trace(1, "--> did not find hello").endif
        ```
        Or use `do(print, msg)` for similar effect (always prints, no tracing required):
        ```python
        p.if_.one('hello').do(print, "--> found hello").else_.do(print, "--> did not find hello").endif
        ```
        """
        if __debug__:
            if self.tracing and self._trace and level <= self._trace[0]: # pylint: disable=unsubscriptable-object
                if callable(msg): msg = msg()
                is_color = self._trace[1] # pylint: disable=unsubscriptable-object
                out = self._trace[2]      # pylint: disable=unsubscriptable-object
                depth = self._lsd + len(self._lookahead_stack)
                self._trace_out(level, is_color, out, ' ' * depth * 2 + msg)
        return self

    @staticmethod
    def is_traceable():
        """Returns True if tracing is possible (i.e. `__debug__` is True and not minified)."""
        return __debug__ and hasattr(Parser, '_trace')

    if __debug__:
        _trace  = None  # None, or (level:int, color:bool, f:callable) level: 0=none, 1=minimal, 5=maximal
        _tracer = None  # Tracer_ instance

        class _Tracer: # Cache for tracing functions
            def __init__(self, p_cls):
                # Lazy import of `inspect` and `re` modules, only if tracing is enabled
                import inspect #pylint: disable=import-outside-toplevel
                import re      #pylint: disable=import-outside-toplevel
                self.inspect_ = inspect
                self.re_      = re

                ec = p_cls.END_CHAR
                def ec_clr(dim): # END_CHAR representation with colors
                    return ('\033[3;38;5;16;48;5;94mᴇᴏꜰ\033[23;39;49m' if dim else
                            '\033[3;38;5;16;48;5;137mᴇᴏꜰ\033[23;39;49m')
                rec = self.re_.compile
                self.colors = {
                    'WARNING':     '\033[91mWARNING\033[39m',
                    '↰ back':      '\033[1;91m↰ back\033[22;39m',
                    '↰ₒₖ back_ok': '\033[1;91m↰ back_ok\033[22;39m',
                    '↴ break':     '\033[1;38;5;125m↴ break\033[22;39m',
                    '↻ continue':  '\033[1;91m↻ continue\033[22;39m',
                    '⏹ end':       '\033[1;91m⏹ end\033[22;39m',
                    '↩ backtrack': '\033[38;5;178m↩ backtrack\033[39m',
                    '✔ commit':    '\033[38;5;28m✔ commit\033[39m',
                    'True':        '\033[92mTrue\033[39m',
                    'False':       '\033[93mFalse\033[39m',
                    '↑ do':        '\033[1;38;5;200m↑ do\033[22;39m',
                    '↑ check':     '\033[1;38;5;99m⇡ check\033[22;39m',
                    '-->':         '\033[90m→\033[39m',
                    '<--':         '\033[90m←\033[39m',
                    '+->':         '\033[38;5;200m↗\033[39m',
                    '\\u2026':     '\u2026', # escaped ellipsis
                    f"'{ec}'":      ec_clr, # '' quoted literal END_CHAR
                    f'"{ec}"':      ec_clr, # "" quoted literal END_CHAR
                    ec:             ec_clr, # literal END_CHAR
                    repr(ec):       ec_clr, # escaped END_CHAR (with quotes)
                    repr(ec)[1:-1]: ec_clr, # escaped END_CHAR (no quotes)
                    rec(r"∈|𝒱|∀|ᵢ|∅|ε"):  r"\033[38;5;116m\g<0>\033[39m", #
                    rec(r"(?<!\w)([A-Za-z_]\w*ᵣ(?:\u0307)?)"): r"\033[38;5;116m\1\033[39m", # colorize subroutine names in cyan
                    rec(r"λ[₀-₉]+"): r"\033[38;5;116m\g<0>\033[39m", # colorize lambda names
                    rec(r"\b(?:not|in)\b"): r"\033[38;5;116m\g<0>\033[39m", # colorize 'not' and other keywords in cyan
                }
                self.level_colors = {1: '196', 2: '208', 3: '220', 4: '111', 5: '245'} # red, orange, yellow, light blue, grey
                # Regex for escapes in strings
                self.re_esc = self.re_.compile(r"\\(?:[nrt'\"\\]|x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})")
                # Regex for quoted strings, '...' or "..." with escapes
                self.re_str = self.re_.compile(r"(['\"])((?:\\.|(?!\1).)*)\1")
            def colorize_str(self, m):
                q, body = m.group(1), m.group(2)
                body = self.re_esc.sub(lambda e: f"\033[38;5;220m{e.group(0)}\033[38;5;215m", body)
                return f"\033[3;38;5;215m{q}{body}{q}\033[23;39m"

        def _trace_out(self, level, is_color, out, msg):
            trc = self._tracer
            f_fixup = {'if_': 'if', 'else_': 'else', 'elif_': 'elif', '_bkt_else': 'backtrack', 'break_': 'break'}
            f_skip  = ('trace', '_trace_out', 'x_', '<lambda>', 'one_with_ctx', '_match_more', '_one_with_trace', '__init__')
            f_abort = ('_fork','_fork_behind') # exit if we hit one of these functions in the stack
            try: # format the call stack chain (left side of the output)
                stack_s = ': '
                stack = trc.inspect_.stack() or []
                prev = prev_prev = ''
                for frame_info in stack: # Iterate over the call stack to find the first non-class method caller
                    f_name = f_fixup.get(frame_info.function, frame_info.function)
                    if f_name in f_abort:  return
                    local_self = frame_info.frame.f_locals.get('self', None)
                    if not isinstance(local_self, (self.__class__, Parser.Branch, Parser.Stop)):
                        # Found the first non-class method (external call) - output and exit
                        f_info = f"{prev_prev}{prev}{f_name}"
                        f_info = f"{f_info:>55}"
                        line_no = f"{frame_info.lineno:04}"
                        if is_color: # Use ANSI escape codes for colored output
                            f_info = f_info.replace('←', '\033[90m←\033[0m') # gray the arrows
                            line_no = f"\033[90m{line_no}\033[0m" # gray the line number
                        stack_s = f" {f_info}:{line_no}   "
                        break
                    if f_name not in f_skip:
                        prev_prev = prev
                        prev = f"{f_name} ← "
            except Exception: # pylint: disable=broad-except
                pass
            # format and colorize the message:
            msg = msg.replace('\n', '\\n').replace('\t', '\\t')
            if is_color: # Use ANSI escape codes for colored output
                is_false = msg.endswith('False')
                msg = str_replace(msg, trc.colors, dim=is_false) # colorize keywords
                msg = trc.re_str.sub(trc.colorize_str, msg) # colorize quoted strings
                if is_false: # dim the entire message if it ends with False
                    msg = f"\033[2m{msg}\033[0m"
                level = f"\033[38;5;{trc.level_colors.get(level, '39')}m{level}\033[39m" # colorize level
            msg = f"{level}{stack_s}{msg}"
            out(msg)

        from contextlib import contextmanager # pylint: disable=import-outside-toplevel
        @contextmanager
        @staticmethod
        def _no_trace(): # disable tracing temporarily (when using parser internally, e.g. in chars())
            t, l = Parser._trace, Parser.PARSE_LIMIT
            Parser._trace, Parser.PARSE_LIMIT = None, 100000
            try:      yield
            finally:  Parser._trace, Parser.PARSE_LIMIT = t, l

        @staticmethod
        @add_static('cache__', {})
        @add_static('brackets__', {'(':')', '[':']', '{':'}'})
        def _lambdas(s): # parse source line for lambda definitions (for tracing)
            # source strings for lambda definitions can get pretty involved, e.g.:
            #    "...p.do(print, "my lambda x: ...").one(lambda x=[(h+5, "hi: ", k[1:5])] : ...)"
            # there can be multiple lambdas on the same line; so we semi-properly parse them.
            if (found := Parser._lambdas.cache__.get(s)) is not None:
                return found # found in cache
            brackets = Parser._lambdas.brackets__

            @parser_subroutine
            def br(p: Parser, bc): # recursive matching of brackets, strings
                closed = Val(False)
                while p.is_active and (p.x0_(p.chars('^([{}])\'"#$')).
                    if_.one(brackets, b := Val()).one(br, b).
                    elif_.one(bc, closed).break_.
                    elif_.one(p.string, on_err=None).else_.end.endif): pass
                return closed

            @parser_subroutine
            def expr(p: Parser, out):
                pos = p.pos
                while p.is_active and (p.x0_(p.chars('^:,([{}])\'"#$')).
                    if_.one(brackets, b := Val()).one(br, b).
                    elif_.one(p.string, on_err=None).else_.break_.endif): pass
                out.append(p.slice_from(pos).strip())
                return True

            @parser_subroutine
            def param(p: Parser, out, **_kwargs): # parse a single param (with default) terminated by , or :
                return p.ws.one(p.identifier, out).ws.if_.one('=').ws.one(expr, Val()).endif

            @parser_subroutine
            def lambda_def(p: Parser, out):
                found = Val(False)
                while p.is_active and (p.x0_(Not(('"', "'", '#', 'lambda', p.END_CHAR))).
                    if_.one('lambda').one(p.collection, param, out=(params := []), brackets={None: ':'}, on_err=None).ws.
                        one(expr, body := Val(), acc=found).do(out.append, (tuple(params), body.v)).break_.
                    elif_.one(p.string, on_err=None).
                    elif_.one(p.END_CHAR).end.
                    else_.break_.endif): pass
                return found

            with Parser._no_trace():
                p, r = Parser(s), []
                while p.is_active and p.x1_(lambda_def, r): pass
            Parser._lambdas.cache__[s] = r # cache the result
            return r # -> list of lambdas: [((param1, param2, ...), body), ...]

        @staticmethod
        def _lambda(f, sr):# Get lambda source code (for tracing)
            try:
                source, lineno = Parser._tracer.inspect_.getsourcelines(f)
            except Exception: # pylint: disable=broad-except
                return 'λ'
            source = source or ''
            if source:
                l = Parser._lambdas(source[0])
                if source := l[0][1] if len(l) == 1 else '': # if multiple lambdas we can't tell which one it is
                    args = f" {', '.join(l[0][0])}" if l[0][0] else ''
                    source = f"{args}: {str_concise(source, 25, True)}"
            lineno = ''.join("₀₁₂₃₄₅₆₇₈₉"[int(d)] for d in str(lineno or '0'))
            return f"λ{lineno}{sr}{source}"

        @staticmethod
        def _f_name(f): # get a friendly name for a callable for tracing
            sr = ('ᵣ' + ('\u0307' if hasattr(f, '__parsek_new_stack') else '')) if hasattr(f, '__parsek_sub') else ''
            if hasattr(f, 'trace_repr'):
                return f.trace_repr() + sr
            if (qname := getattr(f, '__qualname__', '')).startswith(('dict.', 'list.', 'str.')): # str.isalpha, etc.
                f_name = qname
            else:
                f_name = f.__name__ if hasattr(f, '__name__') else f.__class__.__name__ if hasattr(f, '__class__') else str(f)
            return Parser._lambda(f, sr) if f_name == '<lambda>' else f_name + sr

        @staticmethod
        def _v_to_str(v, l=0): # Convert any value to a friendly string (for tracing), l=0 short, 1 - longer, 2 - full
            if hasattr(v, 'trace_repr'):
                return v.trace_repr()
            if isinstance(v, str):
                return "''" if not v else f"{str_concise(v, 15, True)!r}"
            if isinstance(v, (list, tuple, set)):
                if l==0: # just one element,
                    if vs := Parser._v_to_str(v[0]) if v else '':
                        vs = '…' if len(vs) > 12 else vs
                        vs = vs + (',…' if len(v) > 1 else ',' if isinstance(v, tuple) else '')
                    else:
                        vs = ',' if isinstance(v, tuple) else ''
                    return f"({vs})" if isinstance(v, tuple) else f"[{vs}]" if isinstance(v, list) else f"{{{vs}}}"
                vs = str_concise(', '.join(Parser._v_to_str(v_) for v_ in v) if v else '', 15, True)
                return f"({vs},)" if isinstance(v, tuple) else f"[{vs}]" if isinstance(v, list) else f"{{{vs}}}"
            if isinstance(v, Mapping):
                if l==0 and v: # show just one element (if short enough)
                    k, v_ = next(iter(v.items()))
                    if len(vs := f"{Parser._v_to_str(k)}:{Parser._v_to_str(v_)}") <= 12:
                        vs = vs + (',…' if len(v) > 1 else '')
                    else:
                        vs = '…'
                    return f"{{{vs}}}"
                return f"{{{str_concise(', '.join(f'{Parser._v_to_str(k)}:{Parser._v_to_str(v)}' for k, v in v.items()) if v else '', 15, True)}}}"
            if callable(v):
                return Parser._f_name(v)
            return repr(v)

        @staticmethod
        def _f_call_to_str(f, args=None, kwargs=None): # Convert callable to a friendly string for tracing
            f_name = Parser._f_name(f)
            args = ', '.join(Parser._v_to_str(v) for v in args) if args else ''
            if kws := ', '.join(f'{k}={Parser._v_to_str(v)}' for k, v in kwargs.items()) if kwargs else '':
                args += (', ' if args else '') + kws
            if args := str_concise(args, 40, True):
                args = f" <-- {args}" if f_name.startswith('λ') else f"({args})"
            return f_name + args

        @staticmethod
        def _matcher_to_str(f, args=None, kwargs=None): # Friendly name for a matcher (for tracing)
            negate, f = Not.crack(f)
            is_not = 'not ' if negate else ''
            if callable(f):
                return is_not + Parser._f_call_to_str(f, args, kwargs)
            if isinstance(f, (list,tuple, set, Mapping)):
                return f"{is_not}in {Parser._v_to_str(f, 2)})"
            return f"{is_not}{str(f)!r}"

        @staticmethod
        def _units(n, unit) -> str:
            return f"{n} {unit}" if n == 1 else f"{n} {unit}s"

        def _dispatch_one_with_trace(self, f, kwargs):
            ic = kwargs.get('ic', False) # have to get it before _dispatch_one() (it pops it from kwargs for some matchers)
            f_, has_params = self._dispatch_one(f, kwargs)
            return (lambda a=None, k=None, f_og=f, f_one=f_, ic=ic, hp=has_params: self._one_with_trace(f_og, f_one, ic, hp, a, k)), has_params

        def _one_with_trace(self, f_og, f_one, ic, has_params, args=None, kwargs=None):
            ch = self.ch
            start = self.pos
            advance = bool(f_one(args or (), kwargs or {}) if has_params else f_one())
            if self.tracing:
                ch = str_concise(self.slice_from(start), 25, True) if advance else ch
                f_name = self._matcher_to_str(f_og, args, kwargs)
                self.trace(3 if advance else 4, f"{ch!r} --> one({f_name}){'ᵢ' if ic else ''} --> {advance}")
            return advance

class Lookbehind(Parser):
    """Lookbehind parser."""
    class _Source: # Reverse view into parser's source
        __slots__ = ('_s', 'anchor')
        def __init__(self, p: Parser):
            self._s = p.source
            self.anchor = p.pos
        def __len__(self):
            return self.anchor
        def __getitem__(self, key):
            n = self.anchor
            if isinstance(key, int):
                if key < 0:
                    key += n
                return self._s[n - key - 1]
            start, stop, step = key.indices(n) # must be slice or slice-like
            if step == 1:
                if start >= stop:
                    return ''
                return self._s[n - stop:n - start]
            return ''.join(self[i] for i in range(start, stop, step))

    def __init__(self, p: Parser):
        super().__init__(self._Source(p))
