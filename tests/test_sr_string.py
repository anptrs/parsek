""" Test for Parser.string subroutine """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison,unnecessary-lambda
# pylint: disable=broad-exception-raised
# cspell:words heAllo,nllo,Sllo

import pytest
from parsek import Parser, Raw



def test_dec_string_dec():
    """Test the string parser."""

    s = ' 123 "hello \\\" world" -456.78'
    p = Parser(s)
    r = []
    rs = Parser.Val(None)
    p.ws.one(p.decimal, r).ws.one(p.string, rs).trace(1,'hello --> "world"').ws.one(p.decimal, r)
    assert r == [123, -456.78]
    assert rs.value == 'hello " world'



@pytest.mark.parametrize(
    "src, expected_l, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [("'hello'", ["hello"], 8, True),
     ("'hello' ", ["hello"], 9, True),
     ("  'he\\'llo'\n ", ["he'llo"], 14, True),
     ("'hello world, very long string, lorem ipsum Lorem ipsum dolor'",
      ["hello world, very long string, lorem ipsum Lorem ipsum dolor"], 63, True),
     # Try \x \u and \U escapes:
     ("'he\\x20llo'", ["he llo"], 12, True),
     ("'he\\u0041llo'", ["heAllo"], 14, True),
     ("'he\\U00000041llo'", ["heAllo"], 18, True),
     # Octal escapes:
     ("'he\\101llo'", ["heAllo"], 12, True),
     ("'he\\0llo'", ["he\x00llo"], 10, True),
     ("'he\\000llo'", ["he\x00llo"], 12, True),
     ("'he\\12llo'", ["he\nllo"], 11, True),
     ("'he\\012llo'", ["he\nllo"], 12, True),
     ("'he\\123llo'", ["heSllo"], 12, True),
    ]
)
def test_string(src, expected_l, expected_pos, expected_ok):
    """ Tests a the subroutine to parse a quoted string."""
    p = Parser(src)
    l = []

    is_ok = p.ws.one(p.string, l).ws.one(p.END_CHAR).is_ok
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []


@pytest.mark.parametrize(
    "src, kwargs, expected, check_pos",
    [
        ("'hello'", {}, "hello", 7),
        ('"he\\\"llo"', {}, 'he"llo', 9),
        ("''", {}, "", 2),
        ("«test»", {"quotes": {'«': '»', '"': '"', "'": "'"}}, "test", 6),
        ("<a*b>", {"quotes": {'<': '>'}, "replace": {'*': '\uE000'}}, "a\uE000b", 5),
        ('"a\\tb"', {"escapes": {'t': '\t'}}, "a\tb", 6),
        ('"a\\\\b"', {}, r"a\b", 6),
        ('"a\\*b*c"', {"escapes": {'*': '*'}, "replace": {'*': '\uE000'}}, "a*b\uE000c", 8),
    ],
)
def test_string_success_parametrized(src, kwargs, expected, check_pos):

    p = Parser(src)
    out = []
    is_ok = p.one(p.string, out, **kwargs).is_ok
    assert is_ok is True
    assert out == [expected]
    assert p.pos == check_pos
    assert p._lookahead_stack == []


@pytest.mark.parametrize(
    "src, kwargs, expect_exception, expected_ok, expected_pos, err_text",
    [
        # mismatched quote -> reaches EOF -> error (default on_err=True)
        ("'hello\"", {}, ValueError, None, 0, "String must end with a matching quote"),
        # unknown escape -> error
        ('"\\k"', {}, ValueError, None, 0, "Unexpected string escape sequence"),
        # unknown escape but on_err=None -> graceful fail
        ('"\\k"', {"on_err": None}, None, False, 2, ""),
        # opener not in provided quotes -> graceful fail
        ("'hi'", {"quotes": {'<': '>'}}, None, False, 0, ""),
        # EOF inside string with on_err=None -> graceful fail
        ("'unterminated", {"on_err": None}, None, False, 13, ""),
        # Bad \u or \U or \x escape sequence (not enough hex digits) -> error
        ("'bad \\u123 escape'", {}, ValueError, None, 0, "Invalid escape sequence, expected exactly 4 hex digits after \\\\u"),
        ("'bad \\U00123 escape'", {}, ValueError, None, 0, "Invalid escape sequence, expected exactly 8 hex digits after \\\\U"),
        ("'bad \\x1 escape'", {}, ValueError, None, 0, "Invalid escape sequence, expected exactly 2 hex digits after \\\\x"),
        # Bad escape sequence
        ("'bad \\u123'", {}, ValueError, None, 0, "Invalid escape sequence, expected exactly 4 hex digits after \\\\u"),
        ("'bad \\u1'", {}, ValueError, None, 0, "Invalid escape sequence, expected exactly 4 hex digits after \\\\u"),
        ("'bad \\u123", {}, ValueError, None, 0, "Invalid escape sequence, expected exactly 4 hex digits after \\\\u"),
        ("'bad \\U", {}, ValueError, None, 0, "Invalid escape sequence, expected exactly 8 hex digits after \\\\U"),
        ("'bad \\8", {}, ValueError, None, 0, "Unexpected string escape sequence"),
        # Bad return False:
        ("'bad \\u123 escape'", {"on_err": None}, None, False, 7, ""),
    ],
)
def test_string_failure_parametrized(src, kwargs, expect_exception, expected_ok, expected_pos, err_text):

    p = Parser(src)
    out = []

    if expect_exception:
        with pytest.raises(expect_exception, match=err_text):
            p.one(p.string, out, **kwargs)
        # position should not advance on failure with new stack subroutine
        assert p.pos == expected_pos
        assert p._lookahead_stack == []
    else:
        is_ok = p.one(p.string, out, **kwargs).is_ok
        assert is_ok is expected_ok
        # position should not advance on fail
        if expected_ok is False:
            assert p.pos == expected_pos
        assert p._lookahead_stack == []


@pytest.mark.parametrize(
    "src, sink_builder, expected_value, id_",
    [
        # Result sink
        ('"abc"', lambda: Parser.Val(), "abc", "result_sink"),
        # Tuple of Results sink (both receive the same value)
        ('"xyz"', lambda: (Parser.Val(), Parser.Val()), ("xyz", "xyz"), "tuple_of_results_sink"),
        # Dict mapping sink; twice to test default_combiner string concatenation
        ('"abc" "def"', lambda: ({}, 'name'), {"name": "abcdef"}, "dict_mapping_accumulator"),
    ],
)
def test_string_out_sinks(src, sink_builder, expected_value, id_):
    _ = id_  # unused
    p = Parser(src)

    sink = sink_builder()
    if isinstance(sink, tuple) and isinstance(sink[0], dict):
        # dict sink: parse twice to test accumulation
        d, key = sink
        assert p.one(p.string, (d, key)).ws.one(p.string, (d, key)).is_ok
        assert d == expected_value
    elif isinstance(sink, tuple) and all(isinstance(r, Parser.Val) for r in sink):
        r1, r2 = sink
        assert p.one(p.string, (r1, r2)).is_ok
        assert (r1.value, r2.value) == expected_value
    else:
        r = sink  # Parser.Val
        assert p.one(p.string, r).is_ok
        assert r.value == expected_value

def test_string_returns_false_when_invoked_past_end():
    """Covers the final `return False` after the while-loop when called past EOF."""
    p = Parser("")      # empty input
    p.next()            # move past end so the subroutine's while doesn't run
    start_pos = p.pos   # should be len+1 == 1
    out = []

    is_ok = p.one(p.string, out).is_ok
    assert is_ok is False
    assert p.pos == start_pos  # original parser must not advance
    assert out == []           # no output produced
    assert p._lookahead_stack == []





@pytest.mark.parametrize(
    "src, escapes, expected_l, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [("'hello'", Raw(None), ["hello"], 8, True),
     ("'hello' ", Raw({}), ["hello"], 9, True),
     ("  'he\\'llo'\n ", Raw(None), ["he\\'llo"], 14, True),
     # Try \x \u and \U escapes:
     ("'he\\x20llo'", Raw(None), ["he\\x20llo"], 12, True),
     ("'he\\u0041llo'", Raw({}), ["he\\u0041llo"], 14, True),
     ("'he\\U00000041llo'", Raw({}), ["he\\U00000041llo"], 18, True),
     # Octal escapes:
     ("'he\\101llo'", Raw({}), ["he\\101llo"], 12, True),
     ("'he\\0llo'", Raw(None), ["he\\0llo"], 10, True),
     # quotes are still allowed to be escaped:
     ("'he\\'llo' ", Raw({}), ["he\\'llo"], 11, True),
     ('"he\\"llo" ', Raw({}), ["he\\\"llo"], 11, True),
     ("'he\\'llo' ", Raw(None), ["he\\'llo"], 11, True),
     ('"he\\"llo" ', Raw(None), ["he\\\"llo"], 11, True),
     ("'he\\'llo' ", Raw(), ["he\\'llo"], 11, True),
     ('"he\\"llo" ', Raw(), ["he\\\"llo"], 11, True),
    ]
)
def test_string_raw(src, escapes, expected_l, expected_pos, expected_ok):
    """ Tests a the subroutine to parse a quoted string."""
    p = Parser(src)
    l = []

    is_ok = p.ws.one(p.string, l, escapes = escapes).ws.one(p.END_CHAR).is_ok
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []

def test_string_custom_terminator():
    s = ' 123 «hello \\» world» -456.78'
    p = Parser(s)
    r = []
    rs = Parser.Val(None)
    p.ws.one(p.decimal, r).ws.one(p.string, rs, quotes={'«': '»'}, escapes={'»': '»'}).ws.one(p.decimal, r)
    assert r == [123, -456.78]
    assert rs.value == 'hello » world'

def test_string_long_terminator():
    s = ' 123 «hello  worldEND -456.78'
    p = Parser(s)
    r = []
    rs = Parser.Val(None)
    p.ws.one(p.decimal, r).ws.one(p.string, rs, quotes={'«': 'END'}).ws.one(p.decimal, r)
    assert r == [123, -456.78]
    assert rs.value == 'hello  world'

def test_string_callable_terminator():
    """ Tests a the subroutine to parse a quoted string with custom terminator function."""
    s = ' 123 «hello worldEND -456.78'
    p = Parser(s)
    r = []
    rs = Parser.Val(None)
    p.ws.one(p.decimal, r).ws.one(p.string, rs, quotes={'«': p.sr(lambda p: p.one('END'))}).ws.one(p.decimal, r)
    assert r == [123, -456.78]
    assert rs.value == 'hello world'
