""" Test for Parser dynamic loop methods like zero_or_3, one_or_3, x2_3, etc. """
# pylint: disable=protected-access,missing-function-docstring,line-too-long
# cspell:words aaaaaabb,AAAX,AAAB,AAAAAX,AABBBX

import pytest
from parsek import Parser

def test_zero_or_n():
    p = Parser('aaaaaabb')
    r = Parser.Val()
    assert p.zero_to_2('a', r).is_ok
    assert r == 'aa'
    r.reset()
    assert p.three('a', r).is_ok
    assert r == 'aaa'
    r.reset()
    assert r.is_none
    assert not p.three('a', acc=r).is_ok
    assert r.is_none
    assert p.one_to_three('a', acc=r).is_ok
    assert r == 'a'
    assert p.one_to_three('b', acc=r).is_ok
    assert r == 'abb'
    assert p.zero_to_three('b', acc=r).is_ok
    assert r == 'abb'
    r.reset()
    assert p.zero_to_three('b', acc=r).is_ok
    assert r.v is None
    r.reset()
    assert p.zero_to_one('b', acc=r).is_ok
    assert r.v is None

def test_numeric_exactly():
    p = Parser("AAAX")
    r = Parser.Val()
    rv = p.x3('A', acc=r)
    assert rv.is_ok
    assert p.pos == 3
    assert r.value == "AAA"
    assert p.ch == 'X'


def test_numeric_range_2_3():
    p = Parser("AAB")
    rv = p.x2_3('A')
    assert rv.is_ok
    assert p.pos == 2
    assert p.ch == 'B'


def test_numeric_at_least():
    p = Parser("AAAA")
    rv = p.x2_('A')
    assert rv.is_ok
    assert p.pos == 4  # consumed all 'A'


def test_numeric_exactly_fails_and_backtracks():
    p = Parser("AX")
    rv = p.x2('A')
    assert not rv.is_ok
    assert p.pos == 0  # backtracked to start


def test_numeric_range_fails_and_backtracks():
    p = Parser("A")
    rv = p.x2_3('A')
    assert not rv.is_ok
    assert p.pos == 0


def test_spelled_exact_two():
    p = Parser("AAX")
    r = Parser.Val()
    rv = p.two('A', acc=r)
    assert rv.is_ok
    assert p.pos == 2
    assert r.value == "AA"
    assert p.ch == 'X'


def test_spelled_two_or_five():
    p = Parser("AAAAAA")
    r = Parser.Val()
    rv = p.two_to_five('A', acc=r)
    assert rv.is_ok
    assert p.pos == 5  # max of the range
    assert r.value == "AAAAA"


def test_spelled_four_or_more():
    p = Parser("AAAAA")
    rv = p.four_or_more('A')
    assert rv.is_ok
    assert p.pos == 5


def test_dynamic_method_metadata_and_caching():
    p = Parser("AAA")
    m = getattr(p, 'x3')  # triggers __getattr__ and caches on the class
    assert callable(m)
    assert m.__name__ == 'x3'
    assert hasattr(Parser, 'x3')  # cached


def test_positional_and_kwarg_accumulate_exact():
    p = Parser("AAAB")
    r_chars = Parser.Val()
    r_block = Parser.Val()

    rv = p.two('A', r_chars, acc=r_block)
    assert rv.is_ok
    assert p.pos == 2
    assert r_chars.value == "AA"     # accumulated per-iteration by inner one()
    assert r_block.value == "AA"     # accumulated once by outer repeat()
    assert p.ch == 'A'               # next char


def test_positional_and_kwarg_accumulate_range_greedy():
    p = Parser("AAAAAX")
    r_chars = Parser.Val()
    r_block = Parser.Val()

    rv = p.x2_3('A', r_chars, acc=r_block)
    assert rv.is_ok
    assert p.pos == 3                 # capped by upper bound
    assert r_chars.value == "AAA"     # three iterations of inner one()
    assert r_block.value == "AAA"     # single block copied by repeat()
    assert p.ch == 'A'


def test_at_least_consumes_all_available():
    p = Parser("AAAAAX")
    r_chars = Parser.Val()
    r_block = Parser.Val()

    rv = p.x2_('A', r_chars, acc=r_block)
    assert rv.is_ok
    assert p.pos == 5                 # consumed all A's
    assert r_chars.value == "AAAAA"
    assert r_block.value == "AAAAA"
    assert p.ch == 'X'


def test_zero_or_k_positional_unchanged_kwarg_empty_on_zero_match():
    p = Parser("BBB")
    r_chars = Parser.Val()
    r_block = Parser.Val()

    rv = p.zero_to_three('a', r_chars, acc=r_block)
    assert rv.is_ok
    assert p.pos == 0                 # no consumption
    assert r_chars.is_none            # inner one() never called
    assert r_block.value is None      # outer repeat() None


def test_spelled_ic_passthrough():
    p = Parser("AaA!")
    r = Parser.Val()

    rv = p.three('a', acc=r, ic=True)
    assert rv.is_ok
    assert p.pos == 3
    assert r.value == "AaA"           # original casing preserved in copied slice
    assert p.ch == '!'


def test_mixed_spelled_numeric_name_two_or_5():
    p = Parser("AABBBX")
    r1 = Parser.Val()
    r2 = Parser.Val()

    # exactly two A's
    assert p.one_to_three('A', acc=r1).is_ok
    assert r1.value == "AA"
    assert p.ch == 'B'

    # between 2 and 5 B's; here it will consume all 3 B's
    assert p.two_to_5('B', acc=r2).is_ok
    assert r2.value == "BBB"
    assert p.ch == 'X'


def test_mixed_spelled_numeric_name_two_to_5():
    p = Parser("AABBBX")
    r1 = Parser.Val()
    r2 = Parser.Val()

    # exactly two A's
    assert p.one_to_three('A', acc=r1).is_ok
    assert r1.value == "AA"
    assert p.ch == 'B'

    # between 2 and 5 B's; here it will consume all 3 B's
    assert p.two_to_5('B', acc=r2).is_ok
    assert r2.value == "BBB"
    assert p.ch == 'X'

def test_numeric_short_ic_exactly():
    p = Parser("AaAX")
    r = Parser.Val()
    rv = p.x3i('a', acc=r)
    assert rv.is_ok
    assert p.pos == 3
    assert r.value == "AaA"
    assert p.ch == 'X'

def test_numeric_short_ic_range():
    p = Parser("AaAbX")
    rv = p.x2_3i('a')
    assert rv.is_ok
    assert p.pos == 3
    assert p.ch == 'b'

def test_numeric_short_ic_at_least():
    p = Parser("AaAaX")
    rv = p.x2_i('a')
    assert rv.is_ok
    assert p.pos == 4
    assert p.ch == 'X'

def test_numeric_short_ic_exactly_fails_and_backtracks():
    p = Parser("Ax")
    rv = p.x2i('a')
    assert not rv.is_ok
    assert p.pos == 0

def test_ic_aliases_long_and_short():
    p = Parser("AaBb")
    # one_ic
    r1 = Parser.Val()
    assert p.one_ic('a', acc=r1).is_ok
    assert p.pos == 1
    assert r1.value == 'A'
    # zero_or_one_ic -> no match, Nothing copied
    r2 = Parser.Val()
    assert p.zero_or_one_ic('b', acc=r2).is_ok
    assert p.pos == 1  # unchanged
    assert r2.value is None
    # one_or_more_ic
    assert p.one_or_more_ic('a').is_ok
    assert p.pos == 2
    # zero_or_more_ic
    assert p.zero_or_more_ic('b').is_ok
    assert p.pos == 4  # consumed 'Bb'

def test_ic_aliases_short_x_forms():
    # x1i -> exactly one, ic
    p = Parser("A")
    assert p.x1i('a').is_ok
    assert p.pos == 1
    # x0_1i -> zero or one, ic
    p = Parser("Y")
    r = Parser.Val()
    assert p.x0_1i('x', acc=r).is_ok  # no match, zero branch
    assert p.pos == 0
    assert r.value is None

def test_spelled_ic_variants():
    # two_ic
    p = Parser("AaAX")
    r = Parser.Val()
    assert p.two_ic('a', acc=r).is_ok
    assert p.pos == 2
    assert r.value == "Aa"
    assert p.ch == 'A'
    #           0123456
    p = Parser("bBbBbX")
    r = Parser.Val()
    assert p.two_to_five_ic('b', acc=r).one('X').is_ok
    assert p.pos == 6
    assert r.value == "bBbBb"
    assert p.ch == p.END_CHAR
    # two_to_5_ic
    p = Parser("BbBbBX")
    r = Parser.Val()
    assert p.two_to_5_ic('b', acc=r).one('X').is_ok
    assert p.pos == 6
    assert r.value == "BbBbB"
    assert p.ch == p.END_CHAR

def test_spelled_one_to_more_path():
    # "one_to_more" means 1 or more; exercise the '_to_more' code path
    p = Parser("AaAaX")
    r = Parser.Val()
    assert p.one_to_more('a', acc=r, ic=True).is_ok
    assert p.pos == 4
    assert r.value == "AaAa"
    assert p.ch == 'X'

def test_ic_suffix_caching_and_names():
    p = Parser("AAA")
    m1 = p.x3i
    assert callable(m1)
    assert m1.__name__ == 'x3i'
    assert hasattr(Parser, 'x3i')  # cached on class

    m2 = p.two_ic
    assert callable(m2)
    assert m2.__name__ == 'two_ic'
    assert hasattr(Parser, 'two_ic')  # cached on class

def test_invalid_ic_and_short_names():
    p = Parser("A")
    with pytest.raises(AttributeError):
        getattr(p, 'xi')       # missing lower bound
    with pytest.raises(AttributeError):
        getattr(p, 'x_i')      # invalid short form with underscore
    with pytest.raises(AttributeError):
        getattr(p, 'two_or_five_ic')  # illegal spelled form even with _ic

def test_invalids():
    p = Parser("A")
    with pytest.raises(AttributeError):
        getattr(p, 'two_or_')
    with pytest.raises(AttributeError):
        getattr(p, 'two_or')
    with pytest.raises(AttributeError):
        getattr(p, 'two_to_')
    with pytest.raises(AttributeError):
        getattr(p, 'two_to')
    with pytest.raises(AttributeError):
        getattr(p, 'two_or_blah')
    with pytest.raises(AttributeError):
        getattr(p, 'two_or_five')
    with pytest.raises(AttributeError):
        getattr(p, 'x')
    with pytest.raises(AttributeError):
        getattr(p, 'x2_ab')  # invalid upper bound, should raise
