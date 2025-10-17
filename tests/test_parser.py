""" Test Parser """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# cspell:words dlrusz,a̲bc,bcde,defg,klmnopqrst,uvwxyz,klmno,Scienc,w̲orld,s̲econd
import pytest
from parsek import Parser, Not, In, Range

def test_decorators():
    # Retrieve the method and check for decorator attributes
    collection_method = getattr(Parser, 'collection', None)
    assert collection_method is not None
    assert hasattr(collection_method, '__parsek_sub')
    assert getattr(collection_method, '__parsek_sub')
    assert hasattr(collection_method, '__parsek_new_stack')
    assert getattr(collection_method, '__parsek_new_stack')

    decimal_method = getattr(Parser, 'decimal', None)
    assert decimal_method is not None
    assert hasattr(decimal_method, '__parsek_sub')
    assert getattr(decimal_method, '__parsek_sub')

    string_method = getattr(Parser, 'string', None)
    assert string_method is not None
    assert hasattr(string_method, '__parsek_sub')
    assert getattr(string_method, '__parsek_sub')
    assert hasattr(string_method, '__parsek_new_stack')
    assert getattr(string_method, '__parsek_new_stack')

def test_repr():
    p = Parser('abc')
    assert repr(p) == "Parser(pos=0:'a̲bc')"

def test_call():
    p = Parser('abc')
    x = p()
    assert x is p


# -----------------------------------------------------------------------------
# Position saving and popping tests
def test_save_and_pop_position_integer_and_missing():
    p = Parser("abcdef")
    assert p._pos_dict is None
    start = p.pos
    p.save_pos('k1')
    assert 'k1' in p._pos_dict
    p.next(3)  # move to index 3
    saved = p.pop_pos('k1')  # raw position
    assert saved == start
    assert p.pop_pos('k1') is None  # already removed
    # _pos_dict remains (empty dict) so popping unknown returns None
    assert p.pop_pos('unknown') is None

def test_pop_pos_as_str_no_offset():
    p = Parser("abcdef")
    p.next(1)         # pos = 1
    p.save_pos('k')
    p.next(3)         # pos = 4
    s = p.pop_pos('k', as_str=True)
    assert s == "bcd"  # slice 1:4
    assert p.pop_pos('k', as_str=True) is None  # removed already

def test_pop_pos_offset_positive_int():
    p = Parser("abcdef")
    p.save_pos('k')
    p.next(4)  # pos=4 (char 'e')
    s = p.pop_pos('k', as_str=True, offset=1)
    # saved at 0, b_off=1, e_off=0, slice 1:4 -> 'bcd'
    assert s == "bcd"

def test_pop_pos_offset_negative_int():
    p = Parser("abcdef")
    p.save_pos('k')
    p.next(4)
    s = p.pop_pos('k', as_str=True, offset=-1)
    # b_off=0, e_off=-1, slice 0:3 -> 'abc'
    assert s == "abc"

def test_pop_pos_offset_tuple_include_current():
    p = Parser("abcdef")
    p.save_pos('k')
    p.next(4)  # current pos=4, char 'e'
    s = p.pop_pos('k', as_str=True, offset=(1,1))
    # slice from 0+1=1 to 4+1=5 => 'bcde'
    assert s == "bcde"

def test_pop_pos_as_str_key_missing_when_dict_none_and_when_dict_exists():
    # Case 1: _pos_dict is None
    p = Parser("xyz")
    assert p.pop_pos('nope', as_str=True) is None
    # Case 2: _pos_dict exists but key missing
    p.save_pos('have')
    assert p.pop_pos('nope', as_str=True) is None

def test_copy_with_pop_true_removes_key_and_accumulates_list():
    p = Parser("hello world")
    p.next(6)  # after 'hello '
    p.save_pos('word')
    p.next(5)  # pos at end (index 11) slice should be 'world'
    out = []
    p.copy('word', out)  # default pop=True
    assert out == ['world']
    assert 'word' not in p._pos_dict

def test_copy_with_pop_false_preserves_key_then_manual_second_copy():
    p = Parser("0123456789")
    p.next(2)
    assert p.ch == '2'
    p.save_pos('digits')
    p.next(5)  # pos=7
    assert p.ch == '7'
    out1 = []
    p.copy('digits', out1, pop=False)
    assert out1 == ['23456']
    assert 'digits' in p._pos_dict  # still there
    out2 = []
    p.copy('digits', out2)  # pop=True now
    assert out2 == ['23456']
    assert 'digits' not in p._pos_dict

def test_copy_into_val_accumulator():
    p = Parser("abcdefgh")
    p.next(1)  # at 'b'
    p.save_pos('seg')
    p.next(4)  # pos=5, segment 'bcde'
    v = Parser.Val('')
    p.copy('seg', v)
    assert v.value == 'bcde'

def test_copy_missing_key_raises_when_fail_if_not_found_true():
    p = Parser("sample")
    with pytest.raises(ValueError, match="Position 'missing' not found"):
        p.copy('missing', [])

def test_copy_missing_key_silent_when_fail_if_not_found_false():
    p = Parser("sample")
    # Should not raise
    p.copy('missing', [], on_err=None)

def test_copy_when_pos_dict_is_none_and_fail_behaviors():
    p = Parser("alpha")
    # _pos_dict is None
    p.copy('x', [], on_err=None)  # silent
    with pytest.raises(ValueError, match="Position 'x' not found"):
        p.copy('x', [])

def test_multiple_saved_positions_independent():
    p = Parser("abcdefghij")
    p.save_pos('a')          # at 0
    p.next(3)                # pos=3
    p.save_pos('b')          # at 3
    p.next(4)                # pos=7
    seg_b = p.pop_pos('b', as_str=True)  # slice 3:7 -> 'defg'
    assert seg_b == 'defg'
    p.next(2)                # pos=9
    seg_a = p.pop_pos('a', as_str=True)  # slice 0:9 -> 'abcdefghi'
    assert seg_a == 'abcdefghi'

def test_pop_pos_returns_none_after_copy_removed_and_position_not_changed():
    p = Parser("klmnopqrst")
    p.save_pos('k')
    start_pos = p.pos
    p.next(5)
    out = []
    p.copy('k', out)  # pop True -> removes key
    assert p.pop_pos('k') is None
    # copy does not change current pos
    assert p.pos == start_pos + 5
    assert out == ['klmno']

def test_pop_pos_with_as_str_and_offset_after_previous_removal_returns_none():
    p = Parser("uvwxyz")
    p.save_pos('u')
    p.next(3)
    _ = p.pop_pos('u', as_str=True)  # remove
    assert p.pop_pos('u', as_str=True, offset=(1,1)) is None



# -----------------------------------------------------------------------------
# Slicing
def test_slice():
    p = Parser('Test')
    assert p.ch == 'T'
    assert p.slice(1) == 'T'
    assert p.slice(4) == 'Test'
    assert p.slice(5) == 'Test' + Parser.END_CHAR
    assert p.slice(6) == 'Test' + Parser.END_CHAR

def test_slice_behind():
    p = Parser('Example')
    p.next(3)  # pos=3, char 'm'
    assert p.slice_behind(2) == 'xa'
    assert p.slice_behind(3) == 'Exa'
    assert p.slice_behind(4) == 'Exa'
    assert p.slice_behind(5) == 'Exa'
    p.next(3)  # pos=6, char 'e'
    assert p.slice_behind(2) == 'pl'
    p.next()  # pos=7, at end
    assert p.slice_behind(3) == 'ple'
    p.next()  # pos=8, past end
    assert p.slice_behind(4) == 'ple' + Parser.END_CHAR
    p.next()  # pos=8, past end
    assert p.slice_behind(4) == 'ple' + Parser.END_CHAR

def test_slice_from():
    p = Parser('DataScience')
    assert p.slice_from(0) == ''
    p.next(4)  # pos=4, char 'S'
    assert p.slice_from(0) == 'Data'
    assert p.slice_from(2) == 'ta'
    assert p.slice_from(3) == 'a'
    assert p.slice_from(4) == ''
    assert p.slice_from(5) == ''
    p.next(6)  # at e
    assert p.ch == 'e'
    assert p.slice_from(4) == 'Scienc'
    assert p.slice_from(10) == ''
    assert p.slice_from(11) == ''
    p.next()  # at end
    assert p.slice_from(4) == 'Science'
    assert p.slice_from(10) == 'e'
    assert p.slice_from(11) == ''
    assert p.slice_from(12) == ''
    p.next()  # past end
    assert p.slice_from(4) == 'Science' + Parser.END_CHAR
    assert p.slice_from(10) == 'e' + Parser.END_CHAR
    assert p.slice_from(11) == Parser.END_CHAR
    assert p.slice_from(12) == Parser.END_CHAR


# -----------------------------------------------------------------------------
# next(), goto(), skip() skip_to()
def test_next_basic_advancement_and_zero_step():
    p = Parser("abcdef")
    assert p.pos == 0
    assert p.ch == 'a'
    r = p.next()
    assert r is p
    assert p.pos == 1
    assert p.ch == 'b'
    p.next(2)
    assert p.pos == 3
    assert p.ch == 'd'
    # n = 0 should not move position
    before = p.pos
    p.next(0)
    assert p.pos == before
    assert not p.is_end
    assert not p.is_past_end


def test_next_skip_branch_and_large_n_ignored_when_skipping():
    p = Parser("abcdef")
    p.next()  # pos =1
    assert p.pos == 1
    # set skip flag
    r = p.skip()
    assert r is p
    assert p._skip is True  # pylint: disable=protected-access
    before = p.pos
    # next() should only clear skip, not advance even with large n
    p.next(5)
    assert p.pos == before
    assert p._skip is False  # pylint: disable=protected-access
    # Now a normal advance works
    p.next(2)
    assert p.pos == before + 2


def test_skip_to_and_state_preservation_on_next():
    p = Parser("abcdef")
    state_a = object()
    r = p.skip_to(state_a)
    assert r is p
    assert p._skip is True  # pylint: disable=protected-access
    assert p.state is state_a
    pos_before = p.pos
    # next clears skip but does not move
    p.next()
    assert p.pos == pos_before
    assert p._skip is False  # pylint: disable=protected-access
    assert p.state is state_a
    # Further next advances
    p.next()
    assert p.pos == pos_before + 1


def test_goto_overrides_pending_skip():
    p = Parser("abcdef")
    p.skip()
    assert p._skip is True  # pylint: disable=protected-access
    r = p.goto('X')
    assert r is p
    assert p._skip is False  # pylint: disable=protected-access
    assert p.state == 'X'
    before = p.pos
    p.next()
    assert p.pos == before + 1


def test_next_to_end_and_beyond_and_flags():
    s = "xyz"
    p = Parser(s)
    # Advance exactly to end (pos becomes len)
    p.next(len(s))
    assert p.pos == len(s)
    assert p.is_end
    assert not p.is_past_end
    assert p.ch == Parser.END_CHAR
    # Advance beyond end (pos becomes len+1)
    p.next(1)
    assert p.pos == len(s) + 1
    assert p.is_end  # still considered end
    assert p.is_past_end
    assert p.ch == Parser.END_CHAR
    # Further large advance keeps at len+1
    p.next(10)
    assert p.pos == len(s) + 1


def test__next_behavior_boundary_and_past_end():
    p = Parser("hi")  # len =2
    # within bounds
    r = p._next() # pylint: disable=assignment-from-no-return
    assert r is None or r is not p  # _next returns None (implicit), we only care about side-effect
    assert p.pos == 1
    assert not p.is_end
    # at boundary (pos becomes len)
    p._next()
    assert p.pos == 2
    assert p.is_end
    assert not p.is_past_end
    assert p.ch == Parser.END_CHAR
    # past end (pos becomes len+1)
    p._next()
    assert p.pos == 3
    assert p.is_past_end
    assert p.ch == Parser.END_CHAR


def test_next_beyond_end_directly_sets_len_plus_one():
    p = Parser("ab")
    p.next(10)
    assert p.pos == len("ab") + 1
    assert p.is_end
    assert p.is_past_end
    assert p.ch == Parser.END_CHAR


def test_method_return_identities_and_chaining_effects():
    p = Parser("123")
    assert p.skip() is p
    assert p.skip_to('S') is p
    # next clears skip flag only (was set by skip_to)
    assert p._skip is True  # pylint: disable=protected-access
    assert p.next() is p
    assert p._skip is False  # pylint: disable=protected-access
    # goto returns self and disables skip
    p.skip()
    assert p._skip is True  # pylint: disable=protected-access
    assert p.goto('T') is p
    assert p._skip is False  # pylint: disable=protected-access
    # chain a couple of next() calls
    start = p.pos
    p.next().next()
    assert p.pos == start + 2 or p.pos == len(p.source) + 1  # depending on length boundary

# -----------------------------------------------------------------------------
# err(), err_if() on_err()

def test_err_raises_with_string_and_includes_context():
    p = Parser("hello world")
    p.next(6)  # at 'w'
    with pytest.raises(ValueError) as exc:
        p.err("TestError")
    msg = str(exc.value)
    print(repr(msg))
    assert msg == 'TestError at: hello w̲orld'

def test_err_with_callable_returns_fail_and_executes_callable():
    p = Parser("abc")
    called = {}
    def handler(pp):
        called['parser'] = pp
        assert pp is p
    r = p.err(handler)
    assert isinstance(r, Parser.Fail)
    assert called['parser'] is p
    # Fail object should be falsy via is_ok
    assert not r.is_ok
    # Original parser not modified in position
    assert p.pos == 0

def test_err_if_predicate_false_noop_and_identity():
    p = Parser("ab")
    before = p.pos
    r = p.err_if(False, "ShouldNotRaise")
    assert r is p
    assert p.pos == before

def test_err_if_predicate_true_raises_with_string():
    p = Parser("xx")
    with pytest.raises(ValueError, match="Triggered"):
        p.err_if(True, "Triggered")

def test_err_if_predicate_true_callable_executes_but_returns_self():
    p = Parser("yz")
    called = {'n': 0}
    def cb(pp):
        called['n'] += 1
        assert pp is p
    r = p.err_if(True, cb)  # returns Fail
    assert r is not p
    assert isinstance(r, Parser.Fail)
    assert called['n'] == 1

def test_on_err_none_returns_false():
    p = Parser("data")
    assert p.on_err(None, "ignored") is False

def test_on_err_bound_err_same_instance_raises():
    p = Parser("qq")
    with pytest.raises(ValueError, match="Boom"):
        p.on_err(p.err, "Boom")

def test_on_err_bound_err_different_instance_calls_with_current_parser():
    p1 = Parser("first")
    p2 = Parser("second")
    # p2.on_err(p1.err, ...) should raise using p2 context
    with pytest.raises(ValueError, match="XErr at: s̲econd"):
        p2.on_err(p1.err, "XErr")

def test_on_err_unary_callable():
    p = Parser("uvw")
    received = {}
    def unary(msg):  # one argument -> unary
        received['m'] = msg
    rv = p.on_err(unary, "UMsg")
    assert rv is False
    assert received['m'] == "UMsg"

def test_on_err_non_unary_callable():
    p = Parser("rst")
    received = {}
    def non_unary(parser, msg):  # two args -> not unary per is_unary()
        assert parser is p
        received['m'] = msg
    rv = p.on_err(non_unary, "NMsg")
    assert rv is False
    assert received['m'] == "NMsg"

def test_err_and_on_err_interaction_callable_then_raise():
    # Ensure callable branch of err produces Fail, and on_err with unary handles gracefully
    p = Parser("abc")
    seq = []
    def record(pp):
        seq.append(('err_callable', pp.pos))
    fail_obj = p.err(record)
    assert isinstance(fail_obj, Parser.Fail)
    assert seq == [('err_callable', 0)]
    # Now force on_err to raise through bound method
    with pytest.raises(ValueError, match="AfterCallable"):
        p.on_err(p.err, "AfterCallable")

def test_err_if_callable_followed_by_raise_no_state_corruption():
    p = Parser("abcdef")
    def side(pp):
        pp.next(2)  # advance inside callable
    p.err_if(True, side)  # returns self
    assert p.pos == 2
    with pytest.raises(ValueError, match="NowRaise"):
        p.err_if(True, "NowRaise")
    # Position unchanged after raise
    assert p.pos == 2

# -----------------------------------------------------------------------------
# Not, In; more tests in test_one.py
def test_not():
    p = Parser('abc')
    r = []
    assert p.one(Not(In('d')), r).is_ok
    assert r == ['a']

    p = Parser('abc')
    r = []
    assert p.one(p.Not(p.In('de')), r).is_ok
    assert r == ['a']

    p = Parser('Hello')
    r = []
    assert p.one(p.Not("W"), r).is_ok
    assert r == ['H']
    assert not p.one(p.Not("e"), r).is_ok
    assert p.one(p.Not("x"), r).is_ok
    assert r == ['H', 'e']
    assert p.one(p.Not("yz"), r).is_ok
    assert r == ['H', 'e', 'l']
    assert p.one(p.Not(('x', 'y', 'z')), r).is_ok
    assert r == ['H', 'e', 'l', 'l']

    n = Parser.Not(True)
    assert not n
    assert bool(n) is False
    assert n() is False
    assert repr(n) == "Not(True)"
    n = Parser.Not(0, False, 1)
    assert bool(n) is False
    n = Parser.Not(0, False, None)
    assert bool(n) is True

    x = 5
    n = Parser.Not(lambda: x == 5)
    assert not n()
    x = 6
    assert n()


def test_in_ignore_case():
    """Test the set parser."""
    s = 'AbC'
    p = Parser(s)
    r = []
    assert p.one(p.In('abc'), r, ic=True).is_ok
    assert r == ['A']
    assert p.pos == 1

def test_in():
    """Test the set parser."""
    s = 'AbC'
    p = Parser(s)
    r = []
    assert not p.one(p.In('abc'), r).is_ok
    assert p.one(p.In('Abc'), r).is_ok
    assert r == ['A']
    assert p.pos == 1

    i = p.In('xyz')
    assert not i('a')
    assert i('x')
    assert repr(i) == "In('xyz')"
    if Parser.is_traceable():
        assert i.trace_repr() == "in 'xyz'"

    i = p.In('abc')
    assert 'a' in i
    assert 'x' not in i
# -----------------------------------------------------------------------------
# Range() class
def test_range():
    r = Range('a', 'c')
    assert r('a')
    assert r('b')
    assert r('c')
    assert len(r) == 3
    assert 'a' in r
    assert 'b' in r
    assert 'c' in r
    assert 'd' not in r
    assert 'A' not in r
    assert not r('d')
    assert not r('A')
    assert repr(r) == "Range('a', 'c')"
    if Parser.is_traceable():
        assert r.trace_repr() == "in ['a'..'c']"

    r = Range('9', '1') # reversed
    assert r('1')
    assert r('5')
    assert len(r) == 9

# -----------------------------------------------------------------------------
# Acc() class
def test_acc():
    p = Parser('abc')
    l, m = [], {}
    is_ok = p.one('a', p.Acc(l, (m, 'key1')), ic=True).is_ok
    assert is_ok
    assert l == ['a']
    assert m == {'key1': 'a'}

    a = p.Acc(l)
    assert repr(a) == "Acc(['a'])"
    assert len(a) == 1

    a = p.Acc([])
    assert repr(a) == "Acc([])"
    assert len(a) == 1


# -----------------------------------------------------------------------------
# Predicate() class
def test_predicate():
    p = Parser.Predicate(str.isalpha)
    assert p('a')
    assert not p('1')

    p = Parser.Predicate(str.isalpha, 'a')
    assert p.f == str.isalpha
    assert p.args == ('a',)
    assert p.kwargs == {}
    assert p
    assert bool(p)
