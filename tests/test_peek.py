# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# cspell:words abcdef

import pytest
from parsek import Parser, Val, Not, In

def test_peek():
    p = Parser("abcdef")
    r = []
    ok = p.peek('abc', r).one('abc', r).peek('def', r).one('def', r).is_ok
    assert ok
    assert r == ['abc', 'abc', 'def', 'def']
    assert p.pos == len(p.source)
    assert p.is_end

def test_peek_fail():
    p = Parser("abcdef")
    r = []
    ok = p.if_.peek('d').do(r.append, '!').one('abc', r).else_.peek('a').one('abc', r).endif_.is_ok
    assert ok
    assert r == ['abc']
    assert p.pos == 3
    assert not p.is_backtrackable

def test_peek_end_state():
    p = Parser("abc")
    r = []
    assert p.one('abc' + p.END_CHAR).end.is_ok
    assert p.is_end
    assert p.is_past_end
    assert p.is_end_state

    x = p.peek('abc', r)
    assert isinstance(x, Parser.End)
    x = p.peek('abc', r).one('abc', r)
    assert isinstance(x, Parser.End)
    assert r == []
    assert not p.is_backtrackable

def test_peek_sets_end_state():
    p = Parser("abc")
    r = []

    @p.sr
    def sub(p):
        return p.one('abc', r).end()

    x = p.peek(sub, acc=r)
    assert x is p
    assert p.is_end
    assert p.is_end_state

    assert r == ['abc', 'abc']
    assert not p.is_backtrackable
