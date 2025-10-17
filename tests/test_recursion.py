""" Test for recursive subroutines """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# pylint: disable=broad-exception-raised,broad-exception-caught

import pytest
from parsek import Parser, Not, In


BRACKET_TESTS = [
    ("(hello (abc (def) ghi (jkl)) world)""", ["def", 'jkl', "abc  ghi ", "hello  world"], 36, True),
    ("(hello (abc)()(def)(ghi(jkl))world)""", ['abc', '', 'def', "jkl", "ghi", "hello world"], 36, True),
    ("123 (hello (abc)()(def)(ghi(jkl))world)""", ['abc', '', 'def', "jkl", "ghi", "hello world", '123 '], 40, True),
    ("123 (hello (abc)()(def)(ghi(jkl))world)456""", ['abc', '', 'def', "jkl", "ghi", "hello world", '123 456'], 43, True),
    ("(hello (abc)()(def)(ghi(jkl))world)123 """, ['abc', '', 'def', "jkl", "ghi", "hello world", '123 '], 40, True),
]

@pytest.mark.parametrize(
    "src, expected_l, expected_pos, expected_ok", BRACKET_TESTS
)
def test_brackets(src, expected_l, expected_pos, expected_ok):
    """ Tests a recursive subroutine to handle nested brackets: "(hello (abc (def) ghi) world)"""

    p = Parser(src)
    l = []

    @p.subroutine
    def bracketed(p: Parser):
        t = p.Val('')
        b = p.Val(False)  # break flag
        k = 0
        while p.is_active and not b and (p.zero_or_more(Not(In('()' + p.END_CHAR)), t)
                 .if_.one('(').one(bracketed)
                 .elif_.one(')').do(l.append, t.value).do(b.set, True)
                 .else_.one(p.END_CHAR, t).do_if(t, l.append, t.value).end
                 .endif.is_ok):
            if (k := k + 1) > 100: raise Exception("Too much recursion")
        return True

    is_ok = (
        p.if_
            .one(bracketed)
        .endif
        .is_ok
    )
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []


@pytest.mark.parametrize(
    "src, expected_l, expected_pos, expected_ok", BRACKET_TESTS
)
def test_brackets_2(src, expected_l, expected_pos, expected_ok):
    """ Tests a recursive subroutine to handle nested brackets: "(hello (abc (def) ghi) world)"""

    p = Parser(src)
    l = []

    @p.subroutine
    def bracketed(p: Parser):
        t = p.Val('')
        k = 0
        while (p.zero_or_more(p.chars('^()$'), t) # capture any non-bracket characters, one-by-one into t
                 .if_.one('(').one(bracketed) # recursive brackets
                 .elif_.one(p.END_CHAR).do_if(t, l.append, t.value).back
                 .else_.one(')').do(l.append, t.value).fail # finish bracket and break out of the loop
                 .endif):
            if (k := k + 1) > 100: raise Exception("Too much recursion")
        return True

    is_ok = p.one(bracketed).one(p.END_CHAR).is_ok
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []


@pytest.mark.parametrize(
    "src, expected_l, expected_pos, expected_ok", BRACKET_TESTS
)
def test_brackets_2a(src, expected_l, expected_pos, expected_ok):
    """ Tests a recursive subroutine to handle nested brackets: "(hello (abc (def) ghi) world)"""

    p = Parser(src)
    l = []

    @p.subroutine
    def bracketed(p: Parser):
        t = p.Val('')
        k = 0
        while (p.zero_or_more(p.chars('^()$'), acc=t) # capture the whole range of non-bracket characters
                 .if_.one('(').one(bracketed) # recursive brackets
                 .elif_.one(p.END_CHAR).do_if(t, l.append, t.value).back
                 .else_.one(')').do(l.append, t.value).break_ # breaks out of the loop Note; fail == break_ in this context
                 .endif):
            if (k := k + 1) > 100: raise Exception("Too much recursion")
        return True

    is_ok = p.one(bracketed).one(p.END_CHAR).is_ok
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []


@pytest.mark.parametrize(
    "src, expected_l, expected_pos, expected_ok", BRACKET_TESTS
)
def test_brackets_2b(src, expected_l, expected_pos, expected_ok):
    """ Tests a recursive subroutine to handle nested brackets: "(hello (abc (def) ghi) world)"""

    p = Parser(src)
    l = []

    @p.subroutine
    def bracketed(p: Parser):
        t = p.Val('')
        k = 0
        while (p.zero_or_more(Not(In('()' + p.END_CHAR)), t)
                 .if_.one('(').one(bracketed)
                 .elif_.one(')').do(l.append, t.value).break_ # this break will also break the while loop
                 .elif_.one(p.END_CHAR).do_if(t, l.append, t.value).back # and this also stops the while loop and backtracks the END_CHAR which is unnecessary since END_CHAR cannot really be consumed)
                 .endif):
            if (k := k + 1) > 100: raise Exception("Too much recursion")
        return True

    is_ok = p.one(bracketed).one(p.END_CHAR).is_ok
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []
