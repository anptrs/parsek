""" Test Parser.Val """
# pylint: disable=protected-access,missing-function-docstring,missing-class-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison

import pytest
from parsek import Parser



class CustomAccumulator:
    """Custom type with append/clear semantics."""
    def __init__(self):
        self.data = []
    def append(self, v):
        self.data.append(v)
    def clear(self):
        self.data.clear()
    def __repr__(self):
        return f"CustomAccumulator({self.data!r})"


class CustomNoAppend:
    """Custom type without append(); append() on Result should replace value."""
    def __init__(self, v):
        self.v = v
    def clear(self):
        self.v = None
    def __repr__(self):
        return f"CustomNoAppend({self.v!r})"


def test_init_and_basic_equality_truthiness():
    r = Parser.Val()
    assert r.value is None
    assert r.v is None
    assert not r
    r.set(5)
    assert r
    assert r == 5
    assert r == Parser.Val(5)
    assert r != 6


def test_type_properties_and_bool_vs_int():
    assert Parser.Val(True).is_bool
    assert not Parser.Val(True).is_int
    assert Parser.Val(3).is_int
    assert not Parser.Val(3).is_bool
    assert Parser.Val(3.14).is_float
    assert Parser.Val("x").is_str
    assert Parser.Val().is_none


def test_clear_by_type():
    assert Parser.Val("abc").clear().value == ""
    assert Parser.Val(True).clear().value is False
    assert Parser.Val(7).clear().value == 0
    assert Parser.Val(7.2).clear().value == 0.0
    assert Parser.Val().clear().value is None
    c = CustomAccumulator()
    c.append("x")
    r = Parser.Val(c).clear()
    assert r.value.data == []


def test_reset_sets_none():
    r = Parser.Val(10)
    r.reset()
    assert r.value is None
    assert r.is_none


def test_set_scalar_converts_to_current_type():
    r = Parser.Val(10)
    r.set("123")
    assert r.value == 123  # int("123")
    r = Parser.Val(3.5)
    r.set("2")
    assert r.value == 2.0
    r = Parser.Val("abc")
    r.set(42)
    assert r.value == "42"


def test_set_none_clears():
    r = Parser.Val("abc")
    r.set(None)
    assert r.value == ""

def test_is_scalar():
    assert Parser.Val(10).is_scalar
    assert Parser.Val(3.14).is_scalar
    assert Parser.Val("abc").is_scalar
    assert Parser.Val(True).is_scalar
    assert Parser.Val(False).is_scalar
    assert not Parser.Val().is_scalar
    assert not Parser.Val([]).is_scalar


def test_append_with_none_initial_sets_value():
    r = Parser.Val()
    r.append("abc")
    assert r.v == "abc"
    assert r.value == "abc"
    r2 = Parser.Val()
    r2.append([1, 2])
    assert r2.value == [1, 2]


def test_append_string_concatenation():
    r = Parser.Val("hi")
    r.append(" there")
    assert r.value == "hi there"


def test_append_scalar():
    r = Parser.Val(10)
    r.append(99)
    assert r.value == 109
    r = Parser.Val(3.2)
    r.append("5")
    assert r.value == 8.2
    r = Parser.Val("abc")
    r.append(7) # strings are not scalar in Parser contexts
    assert r.value == "abc7"
    r = Parser.Val(True)
    r.append(False)
    assert r.value is True
    r = Parser.Val(False)
    r.append(True)
    assert r.value is True

def test_append_float_to_int():
    r = Parser.Val(10)
    r.append(9.9)
    assert r.value == 19.9
    assert r.is_float


def test_append_custom_with_append_method():
    c = CustomAccumulator()
    r = Parser.Val(c)
    r.append("x").append("y")
    assert c.data == ["x", "y"]


def test_append_custom_without_append_method_replaces():
    c = CustomNoAppend(1)
    r = Parser.Val(c)
    replacement = CustomNoAppend(2)
    r.append(replacement)
    assert r.value is replacement


def test_append_with_result_combiner_on_non_bool_types():
    # Summing lengths of appended strings
    def length_sum(prev, new):
        if prev is None:
            return len(str(new))
        return prev + len(str(new))
    r = Parser.Val().use(length_sum)
    r.append("ab").append("xyz").append("")
    assert r.value == 2 + 3 + 0

def test_append_on_bool_without_combiner_replaces():
    r = Parser.Val(True)
    r.append(False)
    assert r.value is True
    r.append(1)  # bool -> bool(int(1)) -> True
    assert r.value is True


def test_combiner_basic_and_or_xor():
    r = Parser.Val(True).use(Parser.Val.reduce_and)
    r.append(True).append(False)
    assert r.value is False
    r2 = Parser.Val(False).use(Parser.Val.reduce_or)
    r2.append(False).append(True)
    assert r2.value is True
    r3 = Parser.Val(False).use(Parser.Val.reduce_xor)
    r3.append(True).append(True)
    assert r3.value is False  # False xor True -> True; True xor True -> False


def test_combiner_custom_with_initial_none():
    def comb(prev, new):
        if prev is None:
            return new
        return prev + new
    r = Parser.Val().use(comb)
    r.append("a").append("b").append("c")
    assert r.value == "abc"


def test_apply_transforms_and_none_return():
    r = Parser.Val(" hello ")
    r.apply(str.strip)
    assert r.value == "hello"
    # Function returning None (simulating in-place mutation)
    def to_none(_s):
        return None
    r.apply(to_none)
    assert r.value is None


def test_use_sets_combiner():
    r = Parser.Val(True)
    r.use(Parser.Val.reduce_and)
    r.append(True).append(False)
    assert r.value is False


def test_string_is_cctype():
    r = Parser.Val("abc")
    assert r.isspace() is False
    r = Parser.Val("   ")
    assert r.isspace() is True
    r = Parser.Val(42)
    assert r.isspace() is False

def test_string_transforms_on_str():
    r = Parser.Val("  AbC  ")
    r.strip().lower()
    assert r.value == "abc"
    r.upper()
    assert r.value == "ABC"

def test_string_transforms_on_none():
    r = Parser.Val()
    r.strip().lower()
    assert r.value is None
    r.upper()
    assert r.value is None

def test_string_transform_invalid_type_raises():
    r = Parser.Val(123)
    with pytest.raises(ValueError):
        r.lower()


def test_string_transform_respects_subclass_override():
    class LoudStr(str):
        def lower(self):
            return f"LOUD:{super().lower()}"

    r = Parser.Val(LoudStr("HeLLo"))
    r.lower()
    assert r.value == "LOUD:hello"

def test_replace_uses_subclass_override():
    class ReplaceStr(str):
        def replace(self, old, new, count=-1):
            return f"REP({super().replace(old, new, count)})"

    r = Parser.Val(ReplaceStr("ab_ab_ab"))
    r.replace("ab", "X")
    assert r.value == "REP(X_X_X)"

def test_replace_with_mapping_and_standard_overload():
    r = Parser.Val("ab*cd*ef")
    r.replace({'*': '-'})
    assert r.value == "ab-cd-ef"
    r.replace("-", "_")
    assert r.value == "ab_cd_ef"

def test_replace_with_callable_mapping():
    r = Parser.Val("ab*cd*ef")
    r.replace({'*': '-', 'cd': lambda x: f"^{x}^"}, x='XX')
    assert r.value == "ab-^XX^-ef"
    r.replace("-", "_")
    assert r.value == "ab_^XX^_ef"

def test_len_behavior():
    assert len(Parser.Val("abcd")) == 4
    assert len(Parser.Val([1, 2, 3])) == 3
    assert len(Parser.Val(10)) == 0
    assert len(Parser.Val()) == 0


def test_chained_operations():
    r = Parser.Val()
    r.set("").append("Hello").append(", ").append("World").upper().replace({'H': 'J'})
    assert r.value == "JELLO, WORLD"

def test_multi_replace_order():
    r = Parser.Val("abc")
    # Mapping applied in insertion order: a->x then b->y then c->z
    r.replace({'a': 'x', 'b': 'y', 'c': 'z'})
    assert r.value == "xyz"

def test_int_vs_bool():
    r = Parser.Val(42)
    assert not r.is_bool
    assert r.is_int
    assert r == 42
    assert r != 43

    r.clear()
    assert r.value == 0

    # clear a None:
    r.reset()
    assert r.is_none
    r.clear()
    assert r.is_none

    # Bool vs Int
    r = Parser.Val(True)
    assert r.is_bool
    assert not r.is_int
    assert r
    assert r == True  # pylint: disable=singleton-comparison
    assert r != False # pylint: disable=singleton-comparison

def test_inc_from_none_and_int_and_float():
    r = Parser.Val()
    r.inc()  # None -> 1
    assert r.value == 1
    r.inc(4)  # 1 -> 5
    assert r.value == 5
    r.inc(2.5)  # 5 -> 7.5 (int promotes to float)
    assert r.value == 7.5 and r.is_float

    r2 = Parser.Val(10)
    r2.inc()
    assert r2.value == 11
    r2.inc(3)
    assert r2.value == 14

    r3 = Parser.Val(1.5)
    r3.inc()
    assert r3.value == 2.5
    r3.inc(0.5)
    assert r3.value == 3.0

def test_inc_from_bool():
    r = Parser.Val(True)
    r.inc()  # True -> True (step > 0)
    assert r.value is True
    r.inc(2)  # True -> True (step > 0)
    assert r.value is True
    r.inc(0)  # True -> True (step == 0)
    assert r.value is True
    r.inc(-1)  # True -> False (step < 0)
    assert r.value is False
    r.inc(-5)  # False -> False (step < 0)
    assert r.value is False
    r.inc(0)  # False -> False (step == 0)
    assert r.value is False
    r.inc(3)  # False -> True (step > 0)
    assert r.value is True

def test_inc_errors_on_non_numeric():
    with pytest.raises(ValueError):
        Parser.Val("abc").inc()
    with pytest.raises(ValueError):
        Parser.Val([]).inc()


def test_dec_from_none_and_numeric():
    r = Parser.Val()
    r.dec()  # None -> -1
    assert r.value == -1
    r.dec(4)  # -1 -> -5
    assert r.value == -5

    r2 = Parser.Val(10)
    r2.dec()
    assert r2.value == 9
    r2.dec(2)
    assert r2.value == 7

    r3 = Parser.Val(5.0)
    r3.dec(0.5)
    assert r3.value == 4.5


def test_dec_errors_on_non_numeric():
    with pytest.raises(ValueError):
        Parser.Val("xyz").dec()


def test_inc_dec_chaining():
    r = Parser.Val()
    r.inc().inc(2).dec().dec(5)  # None->1->3->2->-3
    assert r.value == -3

def test_iadd():
    r = Parser.Val(10)
    r += 5
    assert r.value == 15
    r += "7"
    assert r.value == 22
    r += 3.5
    assert r.value == 25.5 and r.is_float

    r = Parser.Val('a')
    r += 'b'
    assert r.value == 'ab'
    r += 1
    assert r.value == 'ab1'
    r += 2.5
    assert r.value == 'ab12.5'

def test_is_equal():
    r = Parser.Val()
    assert r != 'hello'
    assert r == None # pylint: disable=singleton-comparison
    assert r == Parser.Val()
    r.set(5)
    assert r == 5
    assert r != 6
    assert r == Parser.Val(5)
