# pylint: disable=protected-access,missing-function-docstring,line-too-long
# cspell:words aaaaa,FGHIJ

import pytest
from parsek import Parser

def test_repeat():
    p = Parser('12345z')
    r = []
    ok = p.repeat(1, 3, str.isdigit, r).is_ok
    assert ok
    assert r == ['1', '2', '3']

    ok = p.repeat(1, 5, str.isdigit, r).is_ok
    assert ok
    assert r == ['1', '2', '3', '4', '5']

    ok = p.repeat(1, 5, str.isdigit, r).is_ok
    assert not ok
    assert r == ['1', '2', '3', '4', '5']

    p.end()
    e = p.repeat(1, 5, str.isdigit, r)
    assert isinstance(e, Parser.End)


def test_repeat_limit():
    prev_limit = Parser.PARSE_LIMIT
    Parser.PARSE_LIMIT = 3
    p = Parser('12345z')
    r = []
    with pytest.raises(ValueError, match="Infinite loop or input too long"):
        _ = p.repeat(1, 6, str.isdigit, r).is_ok

    assert r == ['1', '2', '3', '4']
    #restore limit
    Parser.PARSE_LIMIT = prev_limit

def test_at_least():
    p = Parser('ABCDE_FGHIJ')
    r = []
    ok = p.at_least(3, str.isalpha, r).is_ok
    assert ok
    assert r == ['A', 'B', 'C', 'D', 'E']

    ok = p.at_least(1, str.isalpha, r).is_ok
    assert not ok

    ok = p.at_least_ic(1, '_f', r).is_ok
    assert ok
    assert r == ['A', 'B', 'C', 'D', 'E', '_F']

def test_at_most():
    p = Parser('ABCDE_FGHIJ')
    r = []
    ok = p.at_most(3, str.isalpha, r).is_ok
    assert ok
    assert r == ['A', 'B', 'C']

    ok = p.at_most(5, str.isalpha, r).is_ok
    assert ok
    assert r == ['A', 'B', 'C', 'D', 'E']

    ok = p.at_most(1, str.isalpha, r).is_ok
    assert ok
    assert r == ['A', 'B', 'C', 'D', 'E']

    ok = p.at_most_ic(1, '_f', r).is_ok
    assert ok
    assert r == ['A', 'B', 'C', 'D', 'E', '_F']

def test_exactly():
    p = Parser('ABCDE_FGHIJ')
    r = []
    ok = p.exactly(3, str.isalpha, r).is_ok
    assert ok
    assert r == ['A', 'B', 'C']

    ok = p.exactly(2, str.isalpha, r).is_ok
    assert ok
    assert r == ['A', 'B', 'C', 'D', 'E']

    ok = p.exactly_ic(1, '_f', r).is_ok
    assert ok
    assert r == ['A', 'B', 'C', 'D', 'E', '_F']

def test_zero_or_one():
    p = Parser('12')
    r = []
    ok = p.zero_or_one(str.isdigit, r).is_ok
    assert ok
    assert r == ['1']
    ok = p.zero_or_one(str.isalpha, r).is_ok
    assert ok
    assert r == ['1']
    ok = p.zero_or_one(str.isdigit, r).is_ok
    assert ok
    assert r == ['1', '2']
    ok = p.zero_or_one(str.isdigit, r).is_ok
    assert ok
    assert r == ['1', '2']
    p.end()
    e = p.zero_or_one(str.isdigit, r)
    assert isinstance(e, Parser.End)


def test_zero_or_more():
    p = Parser('123abc')
    r = []
    ok = p.zero_or_more(str.isdigit, r).is_ok
    assert ok
    assert r == ['1', '2', '3']
    ok = p.zero_or_more(str.isdigit, r).is_ok
    assert ok
    assert r == ['1', '2', '3']
    ok = p.zero_or_more(str.isalpha, r).is_ok
    assert ok
    assert r == ['1', '2', '3', 'a', 'b', 'c']
    ok = p.zero_or_more(str.isalpha, r).is_ok
    assert ok
    assert r == ['1', '2', '3', 'a', 'b', 'c']
    p.end()
    e = p.zero_or_more(str.isdigit, r)
    assert isinstance(e, Parser.End)

def test_zero_or_more_nomatch():
    p = Parser('123abc')
    r = []
    ok = p.zero_or_more(str.isalpha, r).is_ok
    assert ok
    ok = p.zero_or_more(str.isdigit, r).is_ok
    assert ok
    assert r == ['1', '2', '3']



def test_zero_or_more_limit():
    prev_limit = Parser.PARSE_LIMIT
    Parser.PARSE_LIMIT = 3
    p = Parser('12345z')
    r = []
    with pytest.raises(ValueError, match="Infinite loop or input too long"):
        _ = p.zero_or_more(str.isdigit, r).is_ok

    assert r == ['1', '2', '3', '4']
    #restore limit
    Parser.PARSE_LIMIT = prev_limit


def test_one_or_more():
    p = Parser('123abc')
    r = []
    ok = p.one_or_more(str.isdigit, r).is_ok
    assert ok
    assert r == ['1', '2', '3']
    ok = p.one_or_more(str.isdigit, r).is_ok
    assert not ok
    assert r == ['1', '2', '3']
    ok = p.one_or_more(str.isalpha, r).is_ok
    assert ok
    assert r == ['1', '2', '3', 'a', 'b', 'c']
    ok = p.one_or_more(str.isalpha, r).is_ok
    assert not ok
    assert r == ['1', '2', '3', 'a', 'b', 'c']
    p.end()
    e = p.one_or_more(str.isdigit, r)
    assert isinstance(e, Parser.End)
