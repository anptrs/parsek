""" Test for Parser.one matcher """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# pylint: disable=broad-exception-raised,unnecessary-lambda
# cspell:words charlix,harlie,fghij,klmno,pqrst,uvwxy,a̲bc,vwxy
import pytest
from parsek import Parser, Not, Predicate


def test_empty_match():
    p = Parser('abc')
    r = []
    is_ok = p.one('', r).is_ok
    assert is_ok
    assert r == ['']
    is_ok = p.one(Not(''), r).is_ok
    assert is_ok
    assert r == ['', 'a']

    is_ok = p.one('b', r).is_ok
    assert is_ok
    assert r == ['', 'a', 'b',]

    is_ok = p.one('', r, ic=True).is_ok
    assert is_ok
    assert r == ['', 'a', 'b', '']

    is_ok = p.one(Not(''), r, ic=True).is_ok
    assert is_ok
    assert r == ['', 'a', 'b', '', 'c']

    is_ok = p.one('', r).is_ok
    assert is_ok
    assert r == ['', 'a', 'b', '', 'c', '']

    is_ok = p.one('', r).is_ok
    assert is_ok
    assert r == ['', 'a', 'b', '', 'c', '', '']

    is_ok = p.one(Not(''), r).is_ok # at EOF
    assert is_ok
    print(r)
    assert r == ['', 'a', 'b', '', 'c', '', '', '']

    is_ok = p.one(Not(''), r).is_ok # past EOF
    assert is_ok
    print(r)
    assert r == ['', 'a', 'b', '', 'c', '', '', '', '']

    is_ok = p.one(Not(''), r).is_ok # past EOF
    assert is_ok
    print(r)
    assert r == ['', 'a', 'b', '', 'c', '', '', '', '', '']

def test_single_char():
    p = Parser('abcd')
    r = set() # empty set
    # No matches:
    is_ok = p.one('A', r).is_ok
    assert not is_ok
    is_ok = p.one(Not('a'), r).is_ok
    assert not is_ok
    is_ok = p.one(Not('A'), r, ic=True).is_ok
    assert not is_ok
    is_ok = p.one('b', r, ic=True).is_ok
    assert not is_ok
    assert r == set()
    # Matches:
    is_ok = p.one('a', r).one('B', r, ic=True).one(Not('b'), r).one(Not('B'), r, ic=True).is_ok
    assert is_ok
    assert r == { 'a', 'b', 'c', 'd' }

def test_str():
    p = Parser('ALPHA BETA CHARLIE DELTA')
    r = []
    # No matches:
    is_ok = p.one('Alpha ', r).is_ok
    assert not is_ok
    is_ok = p.one(Not('ALPHA '), r).is_ok
    assert not is_ok
    is_ok = p.one(Not('alpha '), r, ic=True).is_ok
    assert not is_ok
    is_ok = p.one('beta ', r, ic=True).is_ok
    assert not is_ok
    assert r == []
    # Matches:
    is_ok = p.one('ALPHA ', r).one('beta', r, ic=True).one(Not('CHARLIE'), r).one(Not('charlix'), r, ic=True).is_ok
    assert is_ok
    assert r == ['ALPHA ', 'BETA', ' ', 'C']
    assert p.one('harlie', ic=True).is_ok


def test_lambda():
    p = Parser('abCD')
    r = []
    is_ok = p.one(lambda ch: ch == 'a', r).is_ok
    assert is_ok
    assert r == ['a']
    # Negate
    is_ok = p.one(Not(lambda ch: ch == 'x'), r).is_ok
    assert is_ok
    assert r == ['a' ,'b']
    # IC
    is_ok = p.one(lambda ch: ch == 'c', r, ic=True).is_ok
    assert is_ok
    assert r == ['a', 'b', 'C']
    # Negate IC
    is_ok = p.one(Not(lambda ch: ch == 'x'), r, ic=True).is_ok
    assert is_ok
    assert r == ['a', 'b', 'C', 'D']

    # No match:
    p = Parser('ABCD')
    r = []
    is_ok = p.one(lambda ch: ch == 'x', r).is_ok
    assert not is_ok
    is_ok = p.one(Not(lambda ch: ch == 'A'), r).is_ok
    assert not is_ok
    # IC
    is_ok = p.one(lambda ch: ch == 'x', r, ic=True).is_ok
    assert not is_ok
    # Negate IC
    is_ok = p.one(Not(lambda ch: ch == 'a'), r, ic=True).is_ok
    assert not is_ok
    assert p.pos == 0
    assert r == []


def test_one_callable_with_args():
    def is_set(ch, s, ic=False):
        if ic:
            return ch.upper() in s.upper()
        return ch in s

    p = Parser('abcd')
    r = []
    # No matches:
    is_ok = p.one(is_set, 'xyz', acc=r).is_ok
    assert not is_ok
    is_ok = p.one(Not(is_set), 'abc', acc=r).is_ok
    assert not is_ok
    is_ok = p.one(Not(is_set), 'abc', acc=r, ic=True).is_ok
    assert not is_ok
    is_ok = p.one(is_set, 'xyz', acc=r, ic=True).is_ok
    assert not is_ok
    assert r == []
    # Matches:
    is_ok = p.one(is_set, 'ab', acc=r).one(is_set, 'AB', acc=r, ic=True).\
              one(Not(is_set), 'ab', acc=r).one(Not(is_set),'ab', acc=r, ic=True).is_ok
    assert is_ok
    assert r == ['a', 'b', 'c', 'd']







def test_lambdas():
    p = Parser('abc')
    r = []
    is_ok = p.one(lambda ch: ch == 'a', r).one(lambda ch: ch == 'b', r).is_ok
    assert is_ok
    assert r == ['a', 'b']

def test_lambdas_and_do():
    p = Parser('abc')
    r = []
    is_ok = (p.one(lambda ch: ch == 'a', r).
               one(lambda ch: ch != 'x', r).
               one(lambda ch, x: ch == x, 'c', acc=r).
               check(len, r).
               do_if(Predicate(len, r),lambda k: r.append(k), 'non-empty'). # pylint: disable=unnecessary-lambda
               do(lambda k: r.append(k), 'done'). # pylint: disable=unnecessary-lambda
               do(r.append, 'finished').
               do(print, 'finished').
               is_ok)
    print(r)
    assert is_ok
    assert r == ['a', 'b', 'c', 'non-empty', 'done', 'finished']


def test_char_tuple_to_val():
    s = 'a3'
    p = Parser(s)
    r = Parser.Val(None)
    rn = []
    is_ok = p.one(('b', 'c', 'a'), r).one(str.isdigit, rn).is_ok
    assert is_ok
    assert rn == ['3']
    assert r.value == 'a'
    assert p.pos == 2

def test_char_tuple():
    s = 'a3'
    p = Parser(s)
    r = []
    p.one(('b', 'c', 'a'), r).one(p.decimal, r)
    print(r)
    assert r == ['a', 3]
    assert p.pos == 2

def test_multi_match():
    s = 'abcde 123.4 "klmno" pqrst uvwxy z'
    p = Parser(s)
    r = []
    is_ok = p.three(p.sr(lambda p, out: p.ws.one((p.decimal, p.identifier, p.string), out)), r).one(' ').one('pqrst').is_ok
    assert is_ok
    print(r)
    assert r == [ 'abcde', 123.4, 'klmno',]
    assert p._lookahead_stack == []
    is_ok = p.one(' ').one((p.decimal, p.identifier, p.string), r).one(' z').is_ok
    assert is_ok
    print(r)
    assert r == [ 'abcde', 123.4, 'klmno', 'uvwxy']
    assert p._lookahead_stack == []

def test_multi_no_match():
    s = 'abcde 123.4 ?"klmno" pqrst uvwxy z'
    p = Parser(s)
    r = []
    # @p.subroutine
    # def item_(p, out):
    #     p.ws.if_.one(p.decimal, out).elif_.one(p.identifier, out).else_.one(p.string, out)
    # is_ok = p.three(item_, r)
    is_ok = p.three(p.sr(lambda p, out: p.ws.one((p.decimal, p.identifier, p.string), out)), r).is_ok
    assert not is_ok
    print(r)
    assert r == ['abcde', 123.4]
    assert p.pos == 0
    assert p._lookahead_stack == []

    r = []
    is_ok = p.one((p.decimal, 'abcX', p.string), r).is_ok
    assert not is_ok
    print(r)
    assert r == []
    assert p.pos == 0
    assert p._lookahead_stack == []

    is_ok = p.one((p.decimal, p.string, 'abcX'), r).is_ok
    assert not is_ok
    print(r)
    assert r == []
    assert p.pos == 0
    assert p._lookahead_stack == []

    is_ok = p.one((p.decimal, p.string, Not(str.isalpha)), r).is_ok
    assert not is_ok
    print(r)
    assert r == []
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_multi_no_match_neg():
    s = 'abcde 123.4 "klmno" pqrst uvwxy z'
    p = Parser(s)
    r = []
    is_ok = p.one(Not(p.decimal, p.identifier, p.string), r).is_ok
    assert not is_ok
    print(r)
    assert r == [ 'abcde' ]
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_multi_match_neg():
    s = '? abcde 123.4 "klmno" pqrst uvwxy z'
    p = Parser(s)
    r = []
    is_ok = p.one(Not(p.decimal, p.identifier, p.string), r).is_ok
    assert is_ok
    print(r)
    assert r == [ ]
    assert p.pos == 1
    assert p._lookahead_stack == []



def test_all():
    p = Parser('abcde fghij klmno pqrst uvwxy z1234 56789 0')
    r = []

    @p.subroutine_new_stack
    def sr_(p: Parser, pat):
        return p.ws.one(pat)

    is_ok = (p.one(lambda ch: ch == 'a', r).
               one(lambda ch: ch != 'x', r).
               one(lambda ch, x: ch == x, 'c', acc=r).
               one(('b', 'c', 'd'), r).
               one(('eok', 'elm', 'e f'), r).
               one({'.', '*', 'g'}, r).
               one(['.', '*', 'h'], r).
               one(Not('.', '*', '?'), r).
               one(Not({'.', '*', '?'}), r).
               one(' ', r).
               one({'.', '*', 'K'}, r, ic=True).
               one(Not('.', '*', '?'), r, ic=True).
               one({'.': '*', '?': '!', 'm': 'MMM'}, r).
               one('', r).
               one('', r, ic=True).
               one(Not(''), r).
               one(Not(''), r, ic=True).
               one(p.sr(lambda p: p.ws.one('pq')), acc=r).
               one(p.sr(lambda p, o: p.ws.one('rs', o)), r).
               one(p.sr(sr_), 't', acc=r).
               one(Not(p.sr(lambda p: p.ws.one('x'))), acc=r).   # ' '
               one(Not(p.sr(lambda p, o: p.ws.one('x', o))), r). # 'u' not added to r but consumed
               one(Not(p.sr(sr_)), 'x', acc=r).   # 'v'
               one('wx', r).
               one(Not('YZ'), r).
               one(' Z1', r, ic=True).
               one(Not('??'), r, ic=True).

               check(len, r).
               check(Predicate(len, r)).
               check(Predicate(len), r).
               do_if(Predicate(len, r),lambda k: r.append(k), ' non-empty'). # pylint: disable=unnecessary-lambda
               do(lambda k: r.append(k), ' done'). # pylint: disable=unnecessary-lambda
               do(lambda k, j='default': r.append(k), '.', j="nothing").
               do(lambda a, b: 0, a='A', b="B").
               do(lambda: 42 + 1).
               do(r.append, 'done').
               do(print, 'finished').
               is_ok)
    print(r)
    print(repr(''.join(r)))
    assert is_ok
    assert ''.join(r) == "abcde fghij klMMMno pqrst vwxy z12 non-empty done.done"


#------------------------------------------------------------------------------
# nomatch
def test_nomatch_arg():
    p = Parser('abc')
    r = []
    with pytest.raises(ValueError, match="nope at: a̲bc"):
        is_ok = p.one('x', r, nomatch='nope').is_ok

    is_ok = p.one('x', r, nomatch=lambda p: r.append('nope')).is_ok
    assert not is_ok
    assert r == ['nope']

    # one_with_ctx:
    ctx = p.get_one_ctx('x', r, nomatch=lambda p: r.append('again'))
    is_ok = p.one_with_ctx(ctx).is_ok
    assert not is_ok
    assert r == ['nope', 'again']

def test_end_state():
    p = Parser('abc')
    r = []
    is_ok = p.one('abc', r).end.is_ok
    assert is_ok
    assert r == ['abc']
    assert p.pos == 3
    assert p._lookahead_stack == []
    f = p.one('x', r)
    assert f.is_ok
    assert not f.is_active
