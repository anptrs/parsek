""" Test for Parser.collection subroutine """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# pylint: disable=broad-exception-raised
import re
import pytest
from parsek import Parser



@pytest.mark.parametrize(
    "src, expected_val, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [(" [1, 2, 3, 4] ", [1, 2, 3, 4], 13, True),
     (" [ 1 , 2  , 3   , 4  ] ", [1, 2, 3, 4], 22, True), # with spaces
     ("[]", [], 2, True),                    # empty list no spaces
     ("[   ]", [], 5, True),                 # empty list with spaces
     ("[1,\n2,\n3]", [1,2,3], 9, True),      # newlines
    ]
)
def test_list_of_ints(src, expected_val, expected_pos, expected_ok):
    p = Parser(src)
    l = []

    is_ok = p.ws.one(p.collection, p.decimal, l).is_ok
    assert is_ok is expected_ok
    assert l == expected_val
    assert p.pos == expected_pos
    assert p._lookahead_stack == []



@pytest.mark.parametrize(
    "src, expected_val, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [(" [1, 2, 3, 4] ", [1, 2, 3, 4], 13, True),
     (" [ 1 , 2  , 3   , 4  ] ", [1, 2, 3, 4], 22, True), # with spaces
     (" [1, 'abc', 2, [3, 4, 'def'], 5] ", [1, 'abc', 2, 3, 4, 'def', 5], 32, True), # with spaces
     (" [1, [2, [3, [4]]]] ", [1, 2, 3, 4], 19, True),  # deeper nesting, flatten
    ]
)
def test_recursive_flat_list(src, expected_val, expected_pos, expected_ok):

    p = Parser(src)
    l = []

    @p.subroutine
    def item_(p: Parser, out, **_kwargs):
        return p.if_.one(p.decimal, out).elif_.one(p.string, out).else_.one(p.collection, item_, out).endif

    is_ok = p.ws.one(p.collection, item_, l).is_ok
    assert is_ok is expected_ok
    assert l == expected_val
    assert p.pos == expected_pos
    assert p._lookahead_stack == []


@pytest.mark.parametrize(
    "src, expected_val, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [(" [1, 2, 3, 4] ", [1, 2, 3, 4], 13, True),
     (" [ 1 , 2  , True, 3 , False ,   4  ] ", [1, 2, True, 3, False, 4], 36, True), # with spaces
     (" [1, 'abc', 2.6, [3, 4, 'def'], 5] ", [1, 'abc', 2.6, [3, 4, 'def'], 5], 34, True), # with spaces
     (" [1, 'abc', 2.6, [3, 4, 'def'], [], 5] ", [1, 'abc', 2.6, [3, 4, 'def'], [], 5], 38, True), # empty nested list
     (" [1, 'abc', 2.6, , [3, 4, , 'def'], 5] ", [1, 'abc', 2.6, [3, 4, 'def'], 5], 38, True), # empty items
     (" [1, 'abc', 2.6, [3, 4, 'def'], 5 ", [1, 'abc', 2.6, [3, 4, 'def'], 5], 1, (False, ValueError, "Unclosed collection")), # no closing ], raise
     (" [1, 'abc', 2.6, [3, 4, 'def'], 5 ", [1, 'abc', 2.6, [3, 4, 'def'], 5], 34, (False, None, None)), # no closing ], no raise, just fail
     (" [ ", [], 1, (False, ValueError, "Unclosed collection at:")), # no closing ], raise
     (" x ", [], 1, (False, None, None)), # no opener
     ("", [], 0, (False, None, None)), # no opener
    ]
)
def test_recursive_nested_list(src, expected_val, expected_pos, expected_ok):
    p = Parser(src)
    l = []

    @p.subroutine
    def item_(p: Parser, out, **_kwargs):
        return (p.if_.one(p.decimal, out).
                  elif_.one(p.string, out).
                  elif_.one(('true', 'false'), lambda v: out.append(v.lower() == 'true'), ic=True).
                  else_.one(p.collection, item_, nested_l := []).do(out.append, nested_l).
                  endif)

    exp_e, exp_err_text = None, ""
    on_err = p.err
    if isinstance(expected_ok, tuple):
        expected_ok, exp_e, exp_err_text = expected_ok
        on_err = p.err if exp_e is not None else  None

    if exp_e is not None:
        is_ok = False
        with pytest.raises(exp_e, match=exp_err_text):
            is_ok = p.ws.one(p.collection, item_, l).trace(2, f"collected: {l}").is_ok
    else:
        is_ok = p.ws.one(p.collection, item_, l, on_err=on_err).trace(2, f"collected: {l}").is_ok

    assert is_ok is expected_ok
    assert l == expected_val
    assert p.pos == expected_pos
    assert p._lookahead_stack == []

def test_past_end():
    s = 'a'
    p = Parser(s)
    l = []

    # at the end:
    is_ok = p.one('a').one(p.collection, p.decimal, l).is_ok
    assert is_ok is False
    assert l == []
    assert p.pos == 1
    assert p._lookahead_stack == []
    # past the end:
    is_ok = p.one(p.END_CHAR).one(p.collection, p.decimal, l).is_ok
    assert is_ok is False
    assert p.pos == 2
    assert p._lookahead_stack == []


def test_empty_items():
    s = '[1,,2, ,3, ,]'
    p = Parser(s)
    l = []

    is_ok = p.ws.one(p.collection, p.decimal, l, empty_item=lambda: 42).is_ok
    assert is_ok is True
    assert l == [1,42, 2, 42, 3, 42, 42]
    assert p.pos == 13
    assert p._lookahead_stack == []

@pytest.mark.parametrize(
    "src, expected_val, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [("   { a : 1 , b:2, c : 3, d :4 } ", {'a': 1, 'b': 2, 'c': 3, 'd': 4}, 31, True),
     ("   { a : 1 ,, b:2, c : 3, d :4 } ", {'a': 1, 'b': 2, 'c': 3, 'd': 4}, 32, True), # Empty item
     ("   { a:1, b:2, } ", {'a':1, 'b':2}, 16, True),  # trailing empty item
    ]
)
def test_dict_of_ints(src, expected_val, expected_pos, expected_ok):
    p = Parser(src)
    d = {}

    @p.subroutine
    def item_(p: Parser, out, **_kwargs):
        return p.one(str.isalpha, k := p.Val()).ws.one(':').ws.one(p.decimal, (out, k))

    is_ok = p.ws.one(p.collection, item_, d, brackets={'{': '}'}).is_ok
    assert is_ok is expected_ok
    assert d == expected_val
    assert p.pos == expected_pos
    assert p._lookahead_stack == []



def test_custom_separator():
    p = Parser(" [1; 2;3;4] ")
    l = []
    ok = p.ws.one(p.collection, p.decimal, l, sep=';').is_ok
    assert ok is True
    assert l == [1,2,3,4]
    assert p.pos == len(" [1; 2;3;4] ") - 1  # before trailing space
    assert p.ch == ' '
    assert p._lookahead_stack == []


def test_multiple_separators():
    p = Parser("[1;2,3;4]")
    l = []
    ok = p.one(p.collection, p.decimal, l, sep=(';', ',')).is_ok
    assert ok is True
    assert l == [1,2,3,4]
    assert p.pos == len("[1;2,3;4]")
    assert p._lookahead_stack == []


def test_non_bracketed():
    src = "1, 2, 3, 4"
    p = Parser(src)
    l = []
    ok = p.one(p.collection, p.decimal, l, brackets={None: p.END_CHAR}).is_ok
    assert ok is True
    assert l == [1,2,3,4]
    assert p.pos == len(src) + 1
    assert p._lookahead_stack == []


def test_non_bracketed_trailing_empty_item():
    src = "1,2,3,"
    p = Parser(src)
    l = []
    empty_calls = []
    def empty_item(is_last=False):
        empty_calls.append(is_last)
        return 0 if not is_last else 99
    ok = p.one(p.collection, p.decimal, l, brackets={None: p.END_CHAR}, empty_item=empty_item).is_ok
    assert ok is True
    # last empty becomes 99
    assert l == [1,2,3,99]
    # empty item called twice? once for separator after 3, then last end (END_CHAR) -> expect 2
    assert empty_calls[-1] is True
    assert p.pos == len(src) + 1
    assert p._lookahead_stack == []


def test_opener_already_consumed():
    src = "[5,6]"
    p = Parser(src)
    l = []
    assert p.one('[').is_ok
    ok = p.one(p.collection, p.decimal, l, brackets={None: ']'}).is_ok
    assert ok is True
    assert l == [5,6]
    assert p.pos == len(src)
    assert p._lookahead_stack == []


def test_dict_opener_already_consumed():
    src = "{ a:1, b:2 }"
    p = Parser(src)
    d = {}
    @p.subroutine
    def item_(p: Parser, out, **_k):
        return p.ws.one(str.isalpha, k := p.Val()).ws.one(':').ws.one(p.uint, (out, k))
    assert p.one('{').is_ok
    ok = p.one(p.collection, item_, d, brackets={None: '}'})
    assert ok
    assert d == {'a':1,'b':2}
    assert p.pos == len(src)
    assert p._lookahead_stack == []


def test_empty_dict():
    p = Parser(" {} ")
    d = {}
    @p.subroutine
    def item_(p: Parser, out, **_k):
        return p.one(str.isalpha, k := p.Val()).ws.one(':').ws.one(p.uint, (out, k))
    ok = p.ws.one(p.collection, item_, d, brackets={'{':'}'}).is_ok
    assert ok is True
    assert d == {}
    assert p.pos == 3  # position after '}'
    assert p.ch == ' '
    assert p._lookahead_stack == []


def test_nested_lists_in_dict():
    src = "{ a: [1,2], b: [3, 4] }"
    p = Parser(src)
    d = {}
    @p.subroutine
    def list_item(p: Parser, out, **_k):
        return p.one(p.decimal, out)
    @p.subroutine
    def dict_item(p: Parser, out, **_k):
        return (p.ws.one(str.isalpha, k := p.Val())
                  .ws.one(':')
                  .ws.one(p.collection, list_item, lst := [])
                  .do(lambda: out.__setitem__(str(k), lst)))
    ok = p.one(p.collection, dict_item, d, brackets={'{':'}'}).is_ok
    assert ok is True
    assert d == {'a':[1,2], 'b':[3,4]}
    assert p.pos == len(src)
    assert p._lookahead_stack == []


def test_on_err_suppressed_missing_closer():
    src = "[1,2,3"
    p = Parser(src)
    l = []
    ok = p.one(p.collection, p.decimal, l, on_err=None).is_ok  # suppress error
    assert ok is False
    # items collected before failure
    assert l == [1,2,3]
    assert p.pos == len(src)
    assert p._lookahead_stack == []


def test_invalid_inner_item_error():
    src = "[1, x, 2]"
    p = Parser(src)
    l = []
    with pytest.raises(ValueError, match="Unexpected input for collection"):
        _is_ok = p.one(p.collection, p.decimal, l).is_ok
    # Only first item collected
    assert l == [1]
    # parser advanced up to point of failure (after parsing '1,' and space then 'x')
    assert p._lookahead_stack == []


def test_empty_item_skip_default():
    src = "[,,1,,,2,,]"
    p = Parser(src)
    l = []
    ok = p.one(p.collection, p.decimal, l).is_ok
    # Default empty_item=None so empty elements ignored
    assert ok is True
    assert l == [1,2]
    assert p.pos == len(src)
    assert p._lookahead_stack == []

def test_empty_item_None():
    src = "[,1,,2,3,,]"
    p = Parser(src)
    l = []
    ok = p.one(p.collection, p.decimal, l, empty_item=None).is_ok
    # Default empty_item=None so empty elements ignored
    assert ok is True
    assert l == [1,2,3]
    assert p.pos == len(src)
    assert p._lookahead_stack == []


def test_empty_item_ellipsis():
    src = "[1,,2,]"
    p = Parser(src)
    l = []
    def ei(is_last=False): # pylint: disable=unused-argument
        return ...  # never append
    ok = p.one(p.collection, p.decimal, l, empty_item=ei).is_ok
    assert ok is True
    assert l == [1,2]  # unchanged
    assert p.pos == len(src)
    assert p._lookahead_stack == []

def test_no_opener():
    src = "  1,2,3]"
    p = Parser(src)
    l = []
    ok = p.ws.one(p.collection, p.decimal, l).is_ok
    assert ok is False
    assert l == []
    assert p.pos == 2
    assert p._lookahead_stack == []



def test_collection_empty_separators_ignored_when_empty_item_none():
    # Multiple separators with default empty_item=None must NOT append anything.
    src = "[,,,]"
    p = Parser(src)
    out = []
    ok = p.one(p.collection, p.decimal, out).is_ok
    assert ok is True
    assert out == []              # nothing appended
    assert p.pos == len(src)
    assert p._lookahead_stack == []


def test_collection_empty_separators_with_empty_item_callable_and_trailing():
    # Exercise:
    # - First separator: empty_args_f cache initialization
    # - Subsequent separators: reuse cached args
    # - Trailing comma before ']' -> is_last=True
    src = "[, , ,]"
    p = Parser(src)
    out = []
    calls = []
    def empty_item(is_last=False):
        calls.append(is_last)
        return 0
    ok = p.one(p.collection, p.decimal, out, empty_item=empty_item).is_ok
    assert ok is True
    # Three commas + trailing empty (before ']') -> 4 calls
    assert calls == [False, False, False, True]
    assert out == [0,0,0,0]
    assert p.pos == len(src)
    assert p._lookahead_stack == []


def test_collection_empty_brackets_empty_item_not_called():
    # Ensure empty_item is NOT invoked for immediate close (AFTER_OPENER branch)
    src = "[]"
    p = Parser(src)
    out = []
    called = []
    def empty_item(is_last=False):
        called.append(is_last)
        return 1
    ok = p.one(p.collection, p.decimal, out, empty_item=empty_item).is_ok
    assert ok is True
    assert out == []          # still empty
    assert called == []       # must not be called
    assert p.pos == len(src)
    assert p._lookahead_stack == []

def test_empty_item_branch_false_simple():
    p = Parser("[1,,]")
    out = []
    ok = p.one(p.collection, p.decimal, out).is_ok
    assert ok is True
    assert out == [1]


def test_list_with_string_terminator_consumed():
    # Closing terminator is a multi-character string 'END'
    src = "[1,2,3STOP "
    p = Parser(src)
    out = []
    ok = p.one(p.collection, p.decimal, out, brackets={'[': 'STOP'}).is_ok
    assert ok is True
    assert out == [1, 2, 3]
    # Collection must consume the whole terminator and leave pos at the space after 'STOP'
    assert p.pos == len(src) - 1
    assert p.ch == ' '
    assert p._lookahead_stack == []


def test_list_with_tuple_terminators_consumed_stop():
    # Closing terminator can be any of provided alternatives: ('END', 'STOP')
    src = "[1,2STOP]"
    p = Parser(src)
    out = []
    ok = p.one(p.collection, p.decimal, out, brackets={'[': ('TERM', 'STOP')}).is_ok
    assert ok is True
    assert out == [1, 2]
    # 'STOP' consumed; next char is the trailing ']' which is not part of terminator
    assert p.pos == len(src) - 1
    assert p.ch == ']'
    assert p._lookahead_stack == []


def test_list_with_subroutine_terminator_consumed():
    # Custom subroutine terminator that matches 'END!' exactly
    src = "[10,20END! "
    p = Parser(src)
    out = []

    @p.subroutine
    def end_bang(p: Parser, **_k):
        return p.one("END!").is_ok

    ok = p.one(p.collection, p.int_, out, brackets={'[': end_bang}).is_ok
    assert ok is True
    assert out == [10, 20]
    # Must consume 'END!' and leave pos at the space after it
    assert p.pos == len(src) - 1
    assert p.ch == ' '
    assert p._lookahead_stack == []


def test_non_bracketed_with_string_terminator():
    # Non-bracketed collection that ends with a custom multi-character terminator 'END'
    src = "1,2,3ENDx"
    p = Parser(src)
    out = []
    ok = p.one(p.collection, p.int_, out, brackets={None: 'END'}).is_ok
    assert ok is True
    assert out == [1, 2, 3]
    # Must consume 'END' and leave pos at the trailing 'x'
    assert p.pos == len(src) - 1
    assert p.ch == 'x'
    assert p._lookahead_stack == []


def test_custom_terminator_empty_collection_empty_item_not_called():
    # Ensure empty_item is NOT invoked when the collection immediately closes with custom terminator.
    src = "[END"
    p = Parser(src)
    out = []
    called = []

    def empty_item(is_last=False):
        called.append(is_last)
        return 99

    ok = p.one(p.collection, p.decimal, out, brackets={'[': 'END'}, empty_item=empty_item).is_ok
    assert ok is True
    assert out == []
    assert called == []  # must not be called
    # Consumed 'END'
    assert p.pos == len(src)
    assert p._lookahead_stack == []


def test_custom_terminator_missing_raises():
    # Missing custom terminator should raise the same "Unclosed collection" error
    src = "[1,2,3"
    p = Parser(src)
    out = []
    with pytest.raises(ValueError, match="Unclosed collection"):
        _ = p.one(p.collection, p.int_, out, brackets={'[': 'END'}).is_ok
    # Parser advanced up to end of input
    assert out == [1, 2, 3]
    assert p.pos == 0 # it backtracks because the error is raised, if handled it would be 7
    assert p._lookahead_stack == []

def test_bad_terminator_missing_raises():
    # Missing custom terminator should raise the same "Unclosed collection" error
    src = "[1,2,3EN"
    p = Parser(src)
    out = []
    with pytest.raises(ValueError, match=re.escape("Unexpected input for collection at: [1,2,3E̲N")):
        _ = p.one(p.collection, p.int_, out, brackets={'[': 'END'}).is_ok
    # Parser advanced up to end of input
    assert out == [1, 2, 3]
    assert p.pos == 0 # it backtracks because the error is raised, if handled it would be 7
    assert p._lookahead_stack == []


def test_custom_terminator_missing_err():
    # Missing custom terminator should raise the same "Unclosed collection" error
    src = "[1,2,3"
    p = Parser(src)
    out = []
    err = None
    def set_err(e):
        nonlocal err
        err = str(e)
    ok = p.one(p.collection, p.int_, out, brackets={'[': 'END'}, on_err=set_err).is_ok
    assert ok is False
    assert err == 'Unclosed collection'
    # Parser advanced up to end of input
    assert out == [1, 2, 3]
    assert p.pos == 6
    assert p._lookahead_stack == []
