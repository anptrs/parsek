""" Test accumulation into different targets """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# pylint: disable=missing-class-docstring,unnecessary-lambda,unnecessary-lambda-assignment
# cspell:words resultset
import pytest
from parsek import Parser


class AppendOnly:
    def __init__(self):
        self.data = []
    def append(self, v):
        self.data.append(v)


class AddOnly:
    def __init__(self):
        self.data = set()
    def add(self, v):
        self.data.add(v)


def test_val_and_string_append():
    v = Parser.Val('')
    Parser.accumulate(v, 'ab')
    Parser.accumulate(v, 'cd')
    assert v.value == 'abcd'


def test_list_and_set_add():
    lst = []
    st = set()
    Parser.accumulate(lst, 'x')
    Parser.accumulate(st, 'y')
    assert lst == ['x']
    assert st == {'y'}


def test_resultset_and_nested_and_mapping_tuple():
    d = {}
    v1 = Parser.Val('')
    v2 = Parser.Val('')
    nested = Parser.Acc(Parser.Val(''))
    rs = Parser.Acc(v1, Parser.Acc(v2, nested), (d, 'k'))
    Parser.accumulate(rs, 'A')
    assert v1.value == 'A'
    assert v2.value == 'A'
    assert nested.results[0].value == 'A'
    assert d['k'] == 'A'


def test_empty_tuple_is_noop():
    before = []
    Parser.accumulate((), 'ignored')
    assert before == []  # nothing happened


def test_tuple_of_vals_and_mixed_targets():
    v1 = Parser.Val('')
    v2 = Parser.Val('')
    lst = []
    inner = Parser.Acc(Parser.Val(''))
    targets = (v1, v2, lst, inner)
    Parser.accumulate(targets, 'Z')
    assert v1.value == 'Z'
    assert v2.value == 'Z'
    assert lst == ['Z']
    assert inner.results[0].value == 'Z'


def test_mapping_accumulator_tuple_with_converter():
    d = {}
    Parser.accumulate((d, 'num', int), '5')  # converter path
    Parser.accumulate((d, 'num', int), '7')
    assert d['num'] == 12  # 5 + 7


def test_mapping_accumulator_tuple_with_combiner_two_arg():
    d = {}
    def comb(old, new):
        return (old or 0) + new
    Parser.accumulate((d, 'sum', comb), 3)
    Parser.accumulate((d, 'sum', comb), 4)
    assert d['sum'] == 7


def test_default_combiner_all_branches():
    d = {}
    # old None -> adopt
    Parser.accumulate((d, 'first'), 'X')
    assert d['first'] == 'X'
    # old has append (list)
    Parser.accumulate((d, 'lst'), [])
    Parser.accumulate((d, 'lst'), 'a')
    Parser.accumulate((d, 'lst'), 'b')
    assert d['lst'] == ['a', 'b']
    # bool (old or new)
    Parser.accumulate((d, 'flag'), True)
    Parser.accumulate((d, 'flag'), False)  # stays True
    assert d['flag'] is True
    # string concatenation
    Parser.accumulate((d, 's'), 'ab')
    Parser.accumulate((d, 's'), 'cd')
    assert d['s'] == 'abcd'


def test_mapping_update_dict_update_branch_and_bool_and_list_append():
    d = {}
    # tuple (k, v)
    Parser.accumulate(d, ('name', 'Al'))
    Parser.accumulate(d, ('name', 'ice'))
    assert d['name'] == 'Alice'
    # (k, v, converter)
    Parser.accumulate(d, ('count', '2', int))
    Parser.accumulate(d, ('count', '3', int))
    assert d['count'] == 5
    # mapping literal merge
    Parser.accumulate(d, {'extra': 'Q'})
    Parser.accumulate(d, {'extra': 'Z'})
    assert d['extra'] == 'QZ'
    # list append via default_combiner
    Parser.accumulate(d, ('items', []))
    Parser.accumulate(d, ('items', 'x'))
    Parser.accumulate(d, ('items', 'y'))
    assert d['items'] == ['x', 'y']
    # bool OR logic
    Parser.accumulate(d, ('flag2', False))
    Parser.accumulate(d, ('flag2', True))
    Parser.accumulate(d, ('flag2', False))
    assert d['flag2'] is True


def test_callable_sink_and_error_path():
    collected = []
    sink = lambda v: collected.append(v)
    Parser.accumulate(sink, 'A')
    assert collected == ['A']

    def bad(_v):
        raise RuntimeError("boom")
    with pytest.raises(ValueError) as e:
        Parser.accumulate(bad, 'X')
    assert "Accumulation failed while calling" in str(e.value)


def test_invalid_mapping_accumulator_tuple_error():
    d = {}
    with pytest.raises(ValueError) as e:
        Parser.accumulate((d,), 'x')  # missing key
    assert "Dictionary update failed" in str(e.value)


def test_invalid_out_raises_value_error():
    with pytest.raises(ValueError):
        Parser.accumulate(42, 'x')  # final else branch -> call int -> TypeError -> ValueError


def test_none_out_is_noop():
    # Should not raise
    Parser.accumulate(None, 'ignored')


def test_bool_combination_in_mapping_tuple():
    d = {}
    Parser.accumulate((d, 'flag'), False)
    Parser.accumulate((d, 'flag'), False)
    Parser.accumulate((d, 'flag'), True)
    assert d['flag'] is True
    Parser.accumulate((d, 'flag'), False)  # stays True
    assert d['flag'] is True


def test_dict_append_with_combiner_function_detected_after_typeerror():
    # Provide a "combiner" with two args; attempted as converter raises TypeError -> used as combiner.
    d = {}
    def plus(old, new):
        return (old or 0) + new
    Parser.accumulate((d, 'acc', plus), 1)
    Parser.accumulate((d, 'acc', plus), 5)
    assert d['acc'] == 6

def test_dict_update_iterable_of_pairs_and_triples():
    d = {}
    # iterable of (k, v)
    Parser.accumulate(d, [('x', 'X'), ('y', 'Y')])
    # iterable of (k, v, converter) where converter is unary (int)
    Parser.accumulate(d, [('cnt', '2', int), ('cnt', '3', int)])
    assert d['x'] == 'X'
    assert d['y'] == 'Y'
    assert d['cnt'] == 5  # 2 + 3 via default_combiner after conversion


def test_dict_update_invalid_non_iterable_value_raises():
    d = {}
    with pytest.raises(ValueError):
        Parser.accumulate(d, 123)  # triggers dict_update() final else branch
