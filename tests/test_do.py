
""" Test Parser do/do_if """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# cspell:words capsys

from parsek import Parser
from .helpers import trace_level

def test_do_if():
    p = Parser('!hello world')
    l = []
    is_ok = p.if_.one('!', flag := p.Val(False)).endif.do_if(flag, lambda: p.if_.one('hello', l).endif).ws.one('world')

    assert is_ok
    assert l == ['hello']
    assert p._lookahead_stack == []

def test_do_with_val_applies_function():
    p = Parser("abc")
    v = Parser.Val("abc")
    ret = p.do(v, str.upper)
    assert ret is p
    assert v.v == "ABC"


def test_do_with_plain_function_none_return():
    p = Parser("x")
    called = []
    def side():
        called.append("ok")
    ret = p.do(side)
    assert ret is p
    assert called == ["ok"]


def test_do_function_returns_parser():
    p = Parser("x")
    def ret_p():
        return p
    ret = p.do(ret_p)
    assert ret is p  # early return with the same parser instance


def test_do_function_returns_branch_fail():
    p = Parser("x")
    def make_fail():
        return p.fail  # returns Fail branch
    r = p.do(make_fail)
    assert isinstance(r, Parser.Fail)
    assert not r.is_ok
    # further chained calls stay on Fail
    r2 = r.one("x")  # ignored
    assert r2 is r
    assert p.pos == 0  # no consumption via fail branch


def test_do_function_returns_stop_back():
    p = Parser("xy")
    # Prepare a lookahead so .back is meaningful
    p.lookahead.one("x")
    def do_back():
        return p.back  # Back Stop object
    r = p.do(do_back).endif  # close lookahead chain
    assert isinstance(r, Parser.Back)
    assert not r.is_ok
    # back should restore position to 0
    assert p.pos == 0
    assert p._lookahead_stack == []


def test_do_tracing_enabled_for_val_and_function(capsys):
    # Enable tracing before creating parser
    with trace_level(2, color=False, out=print) as traceable:
        if not traceable:
            return  # or pytest.skip("tracing not available")
        p = Parser("data")
        v = Parser.Val("aa")
        p.do(v, str.upper)
        def f(): return None
        p.do(f)
        out = capsys.readouterr().out
        assert "↑ do" in out


def test_do_if_predicate_false_literal():
    p = Parser("x")
    called = []
    def side():
        called.append(1)
    ret = p.do_if(False, side)
    assert ret is p
    assert called == []


def test_do_if_predicate_true_literal():
    p = Parser("x")
    called = []
    def side():
        called.append(1)
    ret = p.do_if(True, side)
    assert called == [1]
    assert ret is not None  # could be parser


def test_do_if_predicate_object_true():
    p = Parser("x")
    called = []
    def side():
        called.append("hit")
    pred = Parser.P(lambda: True)
    p.do_if(pred, side)
    assert called == ["hit"]


def test_do_if_predicate_object_false():
    p = Parser("x")
    called = []
    def side():
        called.append("hit")
    pred = Parser.P(lambda: False)
    p.do_if(pred, side)
    assert called == []


def test_do_if_val_as_predicate_changes():
    p = Parser("x")
    flag = Parser.Val()  # None -> false
    called = []
    def side():
        called.append("hit")
    p.do_if(flag, side)
    assert called == []
    flag.value = True
    p.do_if(flag, side)
    assert called == ["hit"]


def test_do_if_with_val_target():
    p = Parser("x")
    v = Parser.Val("hi")
    p.do_if(True, v, str.upper)
    assert v.v == "HI"
    # false path no second application
    p.do_if(False, v, str.lower)
    assert v.v == "HI"


def test_do_if_function_returns_branch():
    p = Parser("x")
    def ret_fail():
        return p.fail
    r = p.do_if(True, ret_fail)
    assert isinstance(r, Parser.Fail)
    # ensure no call when predicate false
    calls = []
    def side():
        calls.append(1)
    r2 = p.do_if(False, side)
    assert calls == []
    assert r2 is p  # unchanged parser returned


def test_do_and_do_if_chain_interop():
    p = Parser("abc")
    out = []
    def push_a():
        out.append("A")
    # predicate false: skip, true: execute
    p.do_if(False, push_a).do_if(True, push_a).do(push_a)
    assert out == ["A", "A"]  # only two calls


def test_do_if_with_predicate_val_and_branch_return():
    p = Parser("z")
    flag = Parser.Val(True)
    def produce_branch():
        return p.fail
    r = p.do_if(flag, produce_branch)
    assert isinstance(r, Parser.Fail)
    assert not r.is_ok
