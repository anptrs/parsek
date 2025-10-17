""" Test Parser.chars() """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# cspell:words dlrusz,a̲bc,bcde,defg,klmnopqrst,uvwxyz,klmno,Scienc,w̲orld,s̲econd
import pytest
from parsek import Parser, Not, In, Range

def test_chars_basic():
    p = Parser('abc')
    c1 = p.chars('ab')
    assert c1('a')
    c2 = p.chars('ab')
    assert c1 is c2
    nc1 = p.chars('^ab')
    neg, f = Not.crack(nc1)
    assert neg
    assert f('a')
    nc2 = p.chars('^ab')
    assert nc1 is nc2

@pytest.mark.parametrize("spec, expected", [
    ('a',               'a'),
    ('',                ''),
    ('^',               Not('')),
    ('$',               Parser.END_CHAR),
    ('^$',              Not(Parser.END_CHAR)),
    ('\\^',             '^'),
    ('^a',              Not('a')),
    ('\\^a',            In('^a')),
    ('abc',             In('abc')),
    ('^abc',            Not(In('abc'))),
    ('^abc$',           Not(In('abc' + Parser.END_CHAR))),
    ('^abc$d',          Not(In('abc$d'))),
    ('^a-zA$',          Not(In('abcdefghijklmnopqrstuvwxyzA' + Parser.END_CHAR))),
    ('a-zA$',           In('abcdefghijklmnopqrstuvwxyzA' + Parser.END_CHAR)),
    ('a-zA\\$',         In('abcdefghijklmnopqrstuvwxyzA$')),
    ('a-zA',            In('abcdefghijklmnopqrstuvwxyzA')),
    ('a-z',             In('abcdefghijklmnopqrstuvwxyz')),
    ('--z',             Range('-', 'z')),
    ('a-',              In('a-')),
    ('-a',              In('-a')),
    ('a-z1-9',          In('abcdefghijklmnopqrstuvwxyz123456789')),
    ('a-z-1-9',         In('abcdefghijklmnopqrstuvwxyz123456789-')),
    ('a-z-9',           In('abcdefghijklmnopqrstuvwxyz-9')),
    ('a\\-z-9',         (Range('9', 'z'), In('a-'))),
])
def test_chars(spec, expected):
    got  = Parser.chars(spec)
    print('IN: ', spec)
    print('GOT:', repr(got))
    print('EXP:', expected)
    assert repr(got) == repr(expected)
