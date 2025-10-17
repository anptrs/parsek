""" Test Parser's helper functions and classes """
# pylint: disable=protected-access,missing-function-docstring,missing-class-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# pylint: disable=broad-exception-raised,broad-exception-caught
# cspell:words ghij

import pprint
import pytest
from parsek import Parser, add_static, str_context
from parsek import is_unary

def print_attributes(obj):
    attrs = {}
    for name in dir(obj):
        if name in ('__builtins__', '__globals__'):
            continue
        try:
            attrs[name] = getattr(obj, name)
        except Exception as e:
            attrs[name] = f"<error: {e}>"
    pprint.pprint(attrs)

class UnaryTest:
    def f0(self):
        return 0
    def f1(self, x):
        return x
    def f2(self, x, y):
        return x + y

class UnaryTestCallable:
    def __call__(self, a):
        return 0

class BinaryTestCallable:
    def __call__(self, a, b):
        return 0


def test_is_unary():
    def f(x):
        return x
    def f2(x, y):
        return x + y
    ut = UnaryTest()


    assert is_unary(f)
    assert not is_unary(f2)
    #print_attributes(Parser.In('abc'))
    assert is_unary(Parser.In('abc'))
    #print_attributes(Parser.Not(str.isdigit))

    #print_attributes(UnaryTest.f0)
    assert is_unary(UnaryTest.f0)
    assert not is_unary(UnaryTest.f1)
    assert not is_unary(UnaryTest.f2)
    assert not is_unary(ut.f0)
    assert is_unary(ut.f1)
    assert not is_unary(ut.f2)
    assert is_unary(len)
    assert not is_unary(hasattr)
    #print_attributes(len)
    #print_attributes(UnaryTest.f1)
    print_attributes('he'.isdigit)
    print_attributes(str.isdigit)
    print(f"str.isdigit.hash: {hash(str.isdigit)}")
    assert not is_unary('he'.isdigit)
    assert is_unary(str.isdigit)
    assert not is_unary('he'.isdecimal) # Not cached
    assert is_unary(str.isdecimal) # Not cached

    assert is_unary(UnaryTestCallable())
    assert not is_unary(BinaryTestCallable())

    assert not is_unary(42)


@add_static('_static', 42)
def my_func():
    """ Test func with _static attribute."""
    print(my_func._static)

def test_static():
    my_func()
    assert hasattr(my_func, '_static')
    assert my_func._static == 42

COMB = '\u0332'
def test_str_context():
    assert str_context('{% if b %}...{%endif%}', 6, 20) == '{% if b̲ %}...{%endif%}'

def test_str_context_empty_string():
    assert str_context('', 0) == ''

def test_str_context_whole_no_ellipsis_middle():
    s = 'abc'
    assert str_context(s, 1, context_size=10) == 'a' + 'b' + COMB + 'c'

def test_str_context_clamp_negative_index():
    s = 'abc'
    r = str_context(s, -5)
    assert r == 'a' + COMB + 'bc'
    assert r.count(COMB) == 1

def test_str_context_clamp_large_index_marks_last():
    s = 'abc'
    r = str_context(s, 999)
    assert r == 'ab' + 'c' + COMB
    assert r.count(COMB) == 1

def test_str_context_single_char_string():
    assert str_context('x', 0) == 'x' + COMB

def test_str_context_trailing_ellipsis_only():
    # start == 0, end < len(s)
    s = 'abcdefghij'
    r = str_context(s, 1, context_size=2)
    assert r == 'a' + 'b' + COMB + 'cd' + '…'
    assert r.startswith('ab')
    assert r.endswith('…')
    assert r.count(COMB) == 1

def test_str_context_leading_ellipsis_only():
    # start > 0, end == len(s)
    s = 'abcdefghij'
    r = str_context(s, 8, context_size=2)
    # slice should be 'ghij', mark 'i'
    assert r == '…' + 'gh' + 'i' + COMB + 'j'
    assert r.startswith('…')
    assert not r.endswith('…')
    assert r.count(COMB) == 1

def test_str_context_both_ellipses_unicode_default():
    s = 'abcdefghijklmnopqrstuvwxyz'
    r = str_context(s, 13, context_size=3)  # index 13 -> 'n'
    # window k l m n o p q
    expected = '…klm' + 'n' + COMB + 'opq…'
    assert r == expected
    assert r.startswith('…') and r.endswith('…')
    assert r.count(COMB) == 1

def test_str_context_both_ellipses_ascii_ellipsis():
    s = 'abcdefghijklmnopqrstuvwxyz'
    r = str_context(s, 13, context_size=3, unicode_ellipsis=False)
    expected = '...klm' + 'n' + COMB + 'opq...'
    assert r == expected
    assert r.startswith('...') and r.endswith('...')
    assert r.count(COMB) == 1

def test_str_context_context_size_zero_both_ellipses():
    s = 'abcdef'
    r = str_context(s, 1, context_size=0)  # only char 'b'
    expected = '…' + 'b' + COMB + '…'
    assert r == expected
    assert r.count(COMB) == 1

@pytest.mark.parametrize("s,i,cs", [
    ('hello world', 0, 5),
    ('hello world', 5, 2),
    ('hello world', 10, 5),
])
def test_str_context_combining_char_once(s, i, cs):
    r = str_context(s, i, context_size=cs)
    # Non-empty strings should have exactly one combining underscore
    assert r.count(COMB) == 1
