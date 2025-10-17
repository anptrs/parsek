""" Test for Parser.int/uint/decimal subroutines """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# pylint: disable=broad-exception-raised
import pytest
from parsek import Parser



def test_sr_decimal():
    """Test the decimal parser."""

    s = '123.456 +98.12 -0.56 4 -5 +6 .3 -.4 +.75'
    p = Parser(s)
    r = []
    is_ok = p.one_or_more(p.sr(lambda p, r: p.ws.one(p.decimal, r)), r).is_ok
    assert is_ok
    assert r == [123.456, 98.12, -0.56, 4, -5, 6, 0.3, -0.4, 0.75]
    assert p._lookahead_stack == []

def test_sr_decimal_setter():
    """Test the decimal parser."""
    s = '1 2 3 4'
    p = Parser(s)
    r = []
    def setter(v):
        r.append(v)
    is_ok = p.one_or_more(p.sr(lambda p: p.ws.one(p.decimal, setter))).is_ok
    assert is_ok
    assert r == [1, 2, 3, 4]
    assert p._lookahead_stack == []

def test_sr_decimal_lambda():
    """Test the decimal parser."""

    s = '1 2 3 4'
    p = Parser(s)
    r = []
    is_ok = p.one_or_more(p.sr(lambda p: p.ws.one(p.decimal, lambda v: r.append(v)))).is_ok # pylint: disable=unnecessary-lambda
    assert is_ok
    assert r == [1, 2, 3, 4]
    assert p._lookahead_stack == []

def test_sr_decimal_meth_setter():
    """Test the decimal parser."""

    s = '1 2 3 4'
    p = Parser(s)
    r = []
    is_ok = p.one_or_more(p.sr(lambda p: p.ws.one(p.decimal, r.append))).is_ok
    assert is_ok
    assert r == [1, 2, 3, 4]
    assert p._lookahead_stack == []


@pytest.mark.parametrize("src, expected_val, expected_type, expected_pos",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [(" 123 "   , 123    , int  , 4),
     (" -123 "  , -123   , int  , 5),
     (" 0.456"  , 0.456  , float, 6),
     (" 0"      , 0      , int  , 2),
     ("123"     , 123    , int  , 3),           # integer, no leading ws
     ("123."    , 123.0  , float, 4),      # float with trailing dot (first branch with '.')
     (".5"      , 0.5    , float, 2),          # leading dot (alt branch)
     ("+.5"     , 0.5    , float, 3),         # sign + alt branch
     ("-.5"     , -0.5   , float, 3),        # negative float with leading dot
     ("+0"      , 0      , int  , 2),              # positive sign, int
     ("-0"      , 0      , int  , 2),              # negative zero -> int 0
     ("  .5e2"  , 0.5e2  , float, 6),      # stops before 'e', still valid float
     ("12a34"   , 12     , int  , 2),          # stops before non-digit
     (" +123. " , 123.0  , float, 6),   # leading ws, sign, trailing dot
     ("1.23e4"  , 12300.0, float, 6),  # with exponent
     ("-13"     , -13    , int  , 3),
     ("+0"      , 0      , int  , 2),
     ("3.14"    , 3.14   , float, 4),
     ("-.5"     , -0.5   , float, 3),
     (".5"      , 0.5    , float, 2),
     ("6.02e23" , 6.02e23, float, 7),
     ("-1E-9"   , -1e-9  , float, 5),
     ("+2e+2"   , 200.0  , float, 5),
     ("  +2e+2 ", 200.0  , float, 7),
     ("123abc"  , 123    , int  , 3), # stops before non-digit
     ("-0.99xyz", -0.99  , float, 5), # stops before non-digit
     ("-.5e2foo", -50.0  , float, 5), # stops before non-digit
     ("+3.e2bar", 300.0  , float, 5), # stops before non-digit
    ]
)
def test_decimal(src, expected_val, expected_type, expected_pos):
    """ Tests a the subroutine to parse a quoted string."""

    p = Parser(src)
    l = []

    is_ok = p.ws.one(p.decimal, l).is_ok
    assert is_ok is True
    assert l == [expected_val]
    assert type(l[0]) is expected_type # pylint: disable=unidiomatic-typecheck
    assert p.pos == expected_pos
    assert p._lookahead_stack == []



@pytest.mark.parametrize("src, expected_pos_after, note",[
    ("",      0, "empty input"),
    (" ",     0, "only whitespace (ws advances over one space)"),
    (".",     1, "dot alone should fail and not advance"),
    ("+",     1, "sign alone should fail but sign is consumed before lookahead"),
    ("-.",    2, "dash consumed, then alt branch fails (no digit after '.')"),
    ("+3.e",  3, "bad exponent"),
    ("+3.e+", 3, "bad exponent but we accept it"),
    ("+3.e-", 3, "bad exponent but we accept it"),
    ("abc",   0, "fails: no digits at all"),
    ("--3",   1, "fails: invalid sign"),
    ("++3",   1, "fails: invalid sign"),
    ("+-3",   1, "fails: invalid sign"),
    ("-+3",   1, "fails: invalid sign")]
)
def test_decimal_failures_do_not_match_number(src, expected_pos_after, note):
    p = Parser(src)
    out = []
    is_ok = p.one(p.decimal, out).is_ok
    assert is_ok is False, note
    assert out == []
    assert p.pos == expected_pos_after
    assert p._lookahead_stack == []


def test_decimal_trailing_dot_and_following_char():
    p = Parser("1.a")
    out = []
    assert p.one(p.decimal, out).is_ok
    assert out == [pytest.approx(1.0)]
    assert p.pos == 2  # consumed '1.'
    assert p.ch == 'a'
    assert p._lookahead_stack == []


def test_decimal_accumulates_to_multiple_results():
    p = Parser("42")
    r1 = Parser.Val()
    r2 = Parser.Val()
    targets = (r1, r2)
    assert p.one(p.decimal, targets).is_ok
    assert r1.value == 42
    assert r2.value == 42
    assert p.pos == 2
    assert p._lookahead_stack == []


def test_decimal_accumulates_to_mapping_tuple():
    p = Parser("  .5")
    d = {}
    target = (d, 'num')
    assert p.ws.one(p.decimal, target).is_ok
    assert isinstance(d['num'], float)
    assert d['num'] == pytest.approx(0.5)
    assert p.pos == 4
    assert p._lookahead_stack == []


def test_decimal_accumulates_to_callable():
    p = Parser("-123.")
    captured = []
    def sink(v):
        captured.append(v)
    assert p.one(p.decimal, sink).is_ok
    assert len(captured) == 1
    assert isinstance(captured[0], float)
    assert captured[0] == pytest.approx(-123.0)
    assert p.pos == 5
    assert p._lookahead_stack == []


def test_decimal_result_container():
    p = Parser("  007")
    r = Parser.Val()
    assert p.ws.one(p.decimal, r).is_ok
    assert r.value == 7
    assert p.pos == 5
    assert p._lookahead_stack == []




@pytest.mark.parametrize(
    "src, expected_val, expected_type, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [(" 123 ", 123, int, 4, True),
     (" 0", 0, int, 2, True),
     ("123", 123, int, 3, True),           # integer, no leading ws
     ("-123", -123, int, 4, True),           # integer, no leading ws
     ("+0", 0, int, 2, True),              # positive sign, int
     ("-0", 0, int, 2, True),              # negative zero -> int 0
     ("12a34", 12, int, 2, True),          # stops before non-digit
     ("+", None, int, 1, False),           # just a plus sign is not a number
     ("-", None, int, 1, False),           # just a minus sign is not a number
     ("z", None, int, 0, False),           # just a letter is not a number
     (" z", None, int, 1, False),          # just a letter is not a number
    ]
)
def test_int_(src, expected_val, expected_type, expected_pos, expected_ok):
    """ Tests a the subroutine to parse a quoted string."""

    p = Parser(src)
    l = []

    is_ok = p.ws.one(p.int_, l).is_ok
    assert is_ok is expected_ok
    assert l == ([expected_val] if expected_val is not None else [])
    if expected_val is not None:
        assert type(l[0]) is expected_type # pylint: disable=unidiomatic-typecheck
    assert p.pos == expected_pos
    assert p._lookahead_stack == []



@pytest.mark.parametrize(
    "src, expected_val, expected_type, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [(" 123 ", 123, int, 4, True),
     (" 0", 0, int, 2, True),
     ("123", 123, int, 3, True),           # integer, no leading ws
     ("-123", None, int, 0, False),        # negative integer, should fail
     ("+0", 0, int, 2, True),              # positive sign, int
     ("-0", None, int, 0, False),          # negative zero -> False
     ("12a34", 12, int, 2, True),          # stops before non-digit
     ("+", None, int, 1, False),           # just a plus sign is not a number

    ]
)
def test_uint(src, expected_val, expected_type, expected_pos, expected_ok):
    """ Tests a the subroutine to parse a quoted string."""

    p = Parser(src)
    l = []

    is_ok = p.ws.one(p.uint, l).is_ok
    assert is_ok is expected_ok
    assert l == ([expected_val] if expected_val is not None else [])
    if expected_val is not None:
        assert type(l[0]) is expected_type # pylint: disable=unidiomatic-typecheck
    assert p.pos == expected_pos
    assert p._lookahead_stack == []
