""" Test Parser behind() """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# cspell:words abcdef

import pytest
from parsek import Parser, Lookbehind, Val, Not, In
from .helpers import trace_level

def test_lookbehind():
    p = Parser("abcdef")
    p.pos = 2  # point to 'c'
    b = Lookbehind(p)
    # Source:
    bs = b.source
    assert len(bs) == 2
    assert bs[0] == 'b'
    assert bs[1] == 'a'

    assert b.pos == 0
    assert b.ch == 'b'
    b.next()
    assert b.pos == 1
    assert b.ch == 'a'
    assert not b.is_end
    assert not b.is_past_end
    b.next()
    assert b.pos == 2
    assert b.ch == p.END_CHAR
    assert b.is_end
    assert not b.is_past_end
    b.next()
    assert b.pos == 3
    assert b.ch == p.END_CHAR
    assert b.is_end
    assert b.is_past_end

def test_lookbehind_one():
    p = Parser("abcdef")
    p.pos = 2  # point to 'c'
    b = Lookbehind(p)
    r = []
    ok = b.one('ab', r).is_ok
    assert ok
    assert r == ['ab']

def test_lookbehind_one_more():
    p = Parser("abc'  ")
    p.pos = 3  # point to '
    b = Lookbehind(p)
    r = []
    ok = b.one('c', r).one('ab', r).is_ok
    assert ok
    assert r == ['c', 'ab']

def test_lookbehind_source_slice_and_negative_index():
    p = Parser("abcdef")
    p.pos = len(p.source)
    assert p.ch == p.END_CHAR
    lb = Lookbehind(p)
    # negative index (first char)
    assert lb.source[-1] == 'a'
    # stepped slice (expects order with step 2)
    stepped = lb.source[0:6:2]
    assert stepped == 'fdb'

def test_behind():
    p = Parser(" abc'st' ")
    p.pos = 4  # point to '
    r = []
    ok = p.behind(p.sr(lambda p: p.one('c', r).one('ab', r))).one("'st'", r).is_ok
    assert ok
    assert r == ['c', 'ab', "'st'"]

def test_behind_fail():
    p = Parser(" abc'st' ")
    p.pos = 7  # point to second '
    r = []
    ok = p.behind(p.sr(lambda p: p.one('c', r).one('ab', r))).one("'", r).is_ok
    assert not ok
    assert r == []

def test_behind_basic_success():
    p = Parser("hello world")
    p.pos = p.source.index(' ')  # pos == 5, before space
    out = Val('')
    assert p.behind('hello', out).is_ok
    assert out.v == 'hello'
    assert p.pos == 5  # unchanged


def test_behind_basic_failure():
    p = Parser("hello world")
    p.pos = p.source.index(' ')
    start = p.pos
    r = p.behind('hellO')
    assert not r.is_ok
    assert p.pos == start


def test_behind_nomatch_callable_invoked():
    p = Parser("abcdef")
    p.pos = 3  # after 'abc'
    flag = []
    r = p.behind('xyz', nomatch=lambda _p: flag.append('called'))
    assert not r.is_ok
    assert flag == ['called']
    assert p.pos == 3


def test_behind_nomatch_string_raises():
    p = Parser("abcdef")
    p.pos = 3
    with pytest.raises(ValueError):
        p.behind('xyz', nomatch="expected abc")


def test_behind_at_start():
    p = Parser("abcdef")
    assert p.pos == 0
    r = p.behind('a')
    assert not r.is_ok
    r = p.behind(p.END_CHAR )
    assert r.is_ok
    # empty pattern always succeeds
    empty = Val('')
    assert p.behind('', empty).is_ok
    assert empty.v == ''  # copies empty slice
    assert p.pos == 0


def test_behind_end_of_input_substring():
    s = "abcXYZ"
    p = Parser(s)
    p.pos = len(s)  # at logical end
    out = Val('')
    assert p.behind('XYZ', out).is_ok
    assert out.v == 'XYZ'
    assert p.pos == len(s)


def test_behind_end_of_input_fail_longer():
    s = "abcXYZ"
    p = Parser(s)
    p.pos = len(s)
    assert p.ch == p.END_CHAR
    r = p.behind('abcXYZ')
    assert r.is_ok
    assert p.pos == len(s)
    r = p.behind('abcXYZ_')
    assert not r.is_ok
    assert p.pos == len(s)


def test_behind_one_past_end_unary_predicate_fail():
    p = Parser("abc")
    # Consume END_CHAR to move one past end
    p.one('abc' + p.END_CHAR)
    assert p.pos == len(p.source) + 1
    assert p.is_end
    assert p.is_past_end
    ok = p.behind(str.isalpha) # cannot look behind twice past end of input
    assert not ok.is_ok


def test_behind_ignore_case():
    p = Parser("AbCd")
    p.pos = 4
    v = Val('')
    assert p.behind('abcd', v, ic=True).is_ok
    assert v.v == 'AbCd'
    assert p.pos == 4


def test_behind_unary_single_char():
    p = Parser("abc")
    p.pos = 2  # before 'c', char behind is 'b'
    v = Val('')
    assert p.behind(str.isalpha, v).is_ok
    assert v.v == 'b'
    assert p.pos == 2


def test_behind_not_literal_multi_and_single():
    p = Parser("abZ")
    p.pos = 3
    # Not of multi-char: slice(2) != 'XY' so advances one char (captures 'Z')
    v1 = Val('')
    assert p.behind(Not('XY'), v1).is_ok
    assert v1.v == 'Z'
    # Not of single char equal -> should fail (since ch == 'Z')
    r = p.behind(Not('Z'))
    assert not r.is_ok
    assert p.pos == 3  # unchanged


def test_behind_tuple_alternatives():
    p = Parser("fooBAR")
    p.pos = len("fooBAR")
    v = Val('')
    assert p.behind(('BAR', 'BAZ'), v).is_ok
    assert v.v == 'BAR'


def test_behind_mapping_match():
    p = Parser("xxabyy")
    p.pos = 4  # right before 'yy'; preceding two chars 'ab'
    out = []
    assert p.behind({'ab': 'OK', 'cd': 'NO'}, out).is_ok
    assert out == ['OK']


def test_behind_multiple_accumulators():
    p = Parser("12345")
    p.pos = 5
    v = Val('')
    lst = []
    assert p.behind('345', v, lst).is_ok
    assert v.v == '345'
    assert lst == ['345']
    assert p.pos == 5


def test_behind_empty_pattern_accumulator():
    p = Parser("xyz")
    p.pos = 2
    v = Val('INIT')
    # empty match should not modify value unless slice appended (should append '')
    assert p.behind('', v).is_ok
    assert v.v in ('INIT', 'INIT')  # unchanged effectively
    assert p.pos == 2




def test_behind_in_character_set_and_acc_kw():
    p = Parser("hello123")
    p.pos = len("hello123")
    acc_val = Val('')
    # Use In with acc kw and additional accumulator via positional
    assert p.behind(In('1234567890'), acc=acc_val).is_ok
    assert acc_val.v == '3'
    # Re-run to match preceding digit '2'
    p.pos = len("hello12")
    acc2 = Val('')
    assert p.behind(str.isdigit, acc=acc2).is_ok
    assert acc2.v == '2'


def test_behind_fail_does_not_alter_state():
    p = Parser("abcdef")
    p.pos = 4
    before = p.pos
    r = p.behind('XYZ')
    assert not r.is_ok
    assert p.pos == before
    # subsequent successful call still works
    v = Val('')
    assert p.behind('abcd', v).is_ok
    assert v.v == 'abcd'


def test_behind_chains_with_other_operations():
    p = Parser("token=VALUE;")
    # Move to position just before '='
    p.pos = p.source.index('=')
    # Look behind for identifier, then consume '=' and following uppercase word
    ident = Val('')
    assert p.behind(str.isalpha, ident).is_ok  # captures 'n'
    assert ident.v == 'n'
    ident.v = ''
    # capture full identifier using repeat
    assert p.behind(p.sr(lambda p: p.one_or_more(str.isalpha, acc=ident))).is_ok
    assert ident.v == 'token'
    p.one('=')
    p.repeat(1, 100, str.isupper, acc=(val := Val('')))
    assert val.v == 'VALUE'
    assert p.ch == ';'


@pytest.mark.parametrize(
    "src,pos,pattern,expect_ok,expect_val",
    [
        ("abcXYZ", 6, "XYZ", True, "XYZ"),
        ("abcXYZ", 6, "xyz", False, None),
        ("aaa", 3, "a", True, "a"),
        ("aaa", 2, "aa", True, "aa"),
        ("aaa", 1, "a", True, "a"),
        ("aaa", 0, "a", False, None),
    ]
)
def test_behind_parametrized(src, pos, pattern, expect_ok, expect_val):
    p = Parser(src)
    p.pos = pos
    v = Val('')
    r = p.behind(pattern, v)
    assert bool(r.is_ok) == expect_ok
    if expect_ok:
        assert v.v == expect_val
    else:
        assert v.v == ''  # unchanged default


def test_behind_with_accumulator_tuple_and_dict():
    p = Parser("key123")
    p.pos = len("key123")
    val_acc = Val('')
    count = {}
    # Accumulate into Val, list, and mapping (count occurrences)
    lst = []
    def combiner(old, new):
        return (old or 0) + 1
    assert p.behind('123', val_acc, lst, (count, 'hits', combiner)).is_ok
    assert val_acc.v == '123'
    assert lst == ['123']
    assert count['hits'] == 1

def test_behind_while_in_end_state():
    p = Parser("abc")
    p.end()
    assert p.is_end_state
    r = p.behind('abc')
    assert r.is_ok
    assert isinstance(r, Parser.End)

def test_no_tracing():
    with trace_level(0) as traceable:
        if traceable:
            p_no_trace = Parser("abc")
            r1 = p_no_trace.one('a').behind('a').one('bc')
            assert r1.is_ok

    p2 = Parser("abc")
    r2 = p2.one('a').behind('a').one('bc')
    assert r2.is_ok
