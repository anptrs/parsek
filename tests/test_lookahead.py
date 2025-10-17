""" Test for Parser lookahead/backtrack/alt/merge """
# pylint: disable=protected-access,missing-function-docstring,missing-class-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# pylint: disable=pointless-statement,expression-not-assigned
# cspell:words a̲bc
import pytest
from parsek import Parser
from .helpers import trace_level


def test_alt_first_branch_commits_and_shunts_alt():
    p = Parser('a3!')
    l = []
    is_ok = p.lookahead.one('a', l).alt.one('3', l).merge.is_ok
    # First branch wins, alt is shunted (no side effect from alt branch)
    assert is_ok
    assert l == ['a']
    assert p.pos == 1
    assert p._lookahead_stack == []

def test_alt_second_branch_after_backtrack():
    p = Parser('b3!')
    l = []
    is_ok = p.lookahead.one('a', l).alt.one('b', l).merge.is_ok
    # First branch fails, alt backtracks and second branch consumes
    assert is_ok
    assert l == ['b']
    assert p.pos == 1
    assert p._lookahead_stack == []

def test_alt_both_branches_fail_is_fatal():
    p = Parser('x3!')
    l = []
    is_ok = p.lookahead.one('a', l).alt.one('b', l).merge.is_ok
    assert not is_ok
    assert l == []
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_alt_shunted_branch_has_no_side_effects():
    p = Parser('a3!')
    l = []
    # Alt branch do() should not run when first branch succeeded
    is_ok = p.lookahead.one('a', l).alt.do(list.append, l, 'SHOULD_NOT_FIRE').merge.is_ok
    assert is_ok
    assert l == ['a']
    assert p.pos == 1
    assert p._lookahead_stack == []

def test_alt_yes():
    p = Parser('a3!')
    l = []
    is_ok = p.lookahead.one('a', l).alt.merge.is_ok
    assert is_ok
    assert l == ['a']
    assert p.pos == 1
    assert p._lookahead_stack == []

def test_alt_peek_yes():
    p = Parser('a3!')
    l = []
    is_ok = p.lookahead.one('a', l).fail.alt.merge.is_ok
    assert is_ok
    assert l == ['a']
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_alt_peek_no():
    p = Parser('x3!')
    l = []
    is_ok = p.lookahead.one('a', l).alt.merge.is_ok
    assert is_ok
    assert l == []
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_alt_all_fail_then_new_parse_can_proceed_after_failure():
    # After a fatal alt failure (none match), the parser pos should be restored.
    # A new, independent parse step should still be able to consume input from pos 0.
    p = Parser('b3!')
    l = []
    is_ok = p.lookahead.one('x', l).alt.one('y', l).merge.is_ok
    assert not is_ok
    assert l == []
    assert p.pos == 0
    assert p._lookahead_stack == []

    # Continue parsing with a fresh step
    is_ok2 = p.one('b', l).one('3', l).is_ok
    assert is_ok2
    assert l == ['b', '3']
    assert p.pos == 2
    assert p._lookahead_stack == []

def test_alt_requires_active_lookahead_raises():
    p = Parser('a3!')
    # This only fires in debug mode with assertions enabled:
    if Parser.is_traceable():
        try:
            _ = p.alt  # alt calls commit under the hood; without lookahead this should raise
        except AssertionError as e:
            assert "Lookahead stack is empty" in str(e)
        else:
            assert False, "Expected ValueError when calling alt without active lookahead"

def test_alt_partial_success_then_fail_backtracks_pos_keeps_side_effects():
    # First branch partially succeeds: matches 'a' then fails on '3'
    # Alt branch also fails -> overall fatal; pos backtracks but side-effect from 'a' remains
    p = Parser('a!')
    l = []
    is_ok = p.lookahead.one('a', l).one('3').alt.one('b', l).merge.is_ok
    assert not is_ok
    assert l == ['a']      # side-effect from the successful sub-match is not rolled back
    assert p.pos == 0      # but input consumption is rolled back
    assert p._lookahead_stack == []


# -----------------------------------------------------------------------------
# backtrack / back / back_ok / break_ / continue_

def test_backtrack():
    p = Parser('a3!')
    l = []
    is_ok = p.lookahead.one('a', l).backtrack().is_ok
    assert is_ok
    assert l == ['a']
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_back_multiple_lookaheads_backtracks_all_and_keeps_side_effects():
    p = Parser("ab!")
    out = []
    # Two nested lookaheads consuming 'a' then 'b'
    # After .back we need two .endif to close both lookaheads via Break depth logic
    br = p.if_.one('a', out).if_.one('b', out).back.endif.endif
    assert not br.is_ok              # .back returns Back (is_ok False)
    assert out == ['a', 'b']         # side effects retained
    assert p.pos == 0                # fully backtracked
    assert p._lookahead_stack == []  # stack cleared

def test_back_ok_multiple_lookaheads_true_but_position_restored():
    p = Parser("ab!")
    out = []
    br = p.if_.one('a', out).if_.one('b', out).back_ok.endif.endif
    assert br.is_ok                  # BackOk (True)
    assert out == ['a', 'b']
    assert p.pos == 0                # backtracked (not committed)
    assert p._lookahead_stack == []

def test_back_requires_active_lookahead_raises():
    if Parser.is_traceable():
        p = Parser("abc")
        with pytest.raises(AssertionError):
            _ = p.back.endif  # triggers parent.backtrack() assertion (empty stack)

def test_back_end_state_returns_end():
    p = Parser("")
    p.end
    e = p.back
    assert e.is_ok                  # End sentinel
    assert isinstance(e, Parser.End)

def test_back_ok_end_state_returns_end():
    p = Parser("")
    p.end
    e = p.back_ok
    assert e.is_ok
    assert isinstance(e, Parser.End)

def test_back_and_then_new_parse_proceeds():
    p = Parser("ab")
    out = []
    p.if_.one('a', out).back.endif  # backtracked
    assert p.pos == 0
    assert out == ['a']
    # Start fresh parse
    p.one('a').one('b', out)
    assert out == ['a', 'b']
    assert p.pos == 2

def test_back_vs_break_difference():
    p1 = Parser("ab")
    a1 = []
    p1.if_.one('a', a1).if_.one('b', a1).back.endif.endif
    assert p1.pos == 0           # backtracked
    assert a1 == ['a', 'b']

    p2 = Parser("ab")
    a2 = []
    p2.if_.one('a', a2).if_.one('b', a2).break_.endif.endif
    assert p2.pos == 2           # committed
    assert a2 == ['a', 'b']

def test_back_ok_truthiness_and_cleanup():
    p = Parser("ab")
    out = []
    r = p.if_.one('a', out).if_.one('b', out).back_ok.endif.endif
    assert r.is_ok
    assert p.pos == 0
    assert out == ['a', 'b']
    assert p._lookahead_stack == []

def test_branch_class():
    p = Parser("abc")
    b = p.one('b') # <-- Fail
    assert isinstance(b, Parser.Branch)
    assert isinstance(b, Parser.Fail)
    assert repr(b) == "Fail(parent=Parser(pos=0:'a̲bc'))"

def test_break_single_lookahead_commits_and_false():
    p = Parser("abc")
    out = []
    br = p.if_.one('a', out).break_.endif
    # break_ commits lookahead, advances pos (one char consumed)
    assert not br.is_ok
    assert out == ['a']
    assert p.pos == 1
    assert p._lookahead_stack == []

def test_break_nested_depth_path():
    p = Parser("ab!")
    out = []
    # Add an extra .if_ AFTER break_ to exercise the path where first .endif
    # does not close (_close deferred until depth drops below watermark)
    br = p.if_.one('a', out).break_.if_.endif.endif
    assert not br.is_ok
    assert out == ['a']
    assert p.pos == 1                # committed (not backtracked)
    assert p._lookahead_stack == []

def test_break_requires_active_lookahead_raises():
    if Parser.is_traceable():
        p = Parser("x")
        with pytest.raises(AssertionError):
            _ = p.break_.endif

def test_break_end_state_returns_end():
    p = Parser("")
    p.end
    e = p.break_
    assert e.is_ok                   # End sentinel treated as ok
    assert isinstance(e, Parser.End)

def test_break_and_continue_do_not_leave_stack():
    p = Parser("abcdef")
    out_b = []
    out_c = []
    p.if_.one('a', out_b).break_.endif
    assert p._lookahead_stack == []

    p.if_.one('b', out_c).continue_.endif
    assert p._lookahead_stack == []
    assert out_b == ['a']
    assert out_c == ['b']

def test_continue_single_lookahead_commits_and_true():
    p = Parser("abc")
    out = []
    br = p.if_.one('a', out).continue_.endif
    assert br.is_ok
    assert out == ['a']
    assert p.pos == 1
    assert p._lookahead_stack == []

def test_continue_nested_depth_path():
    p = Parser("ab!")
    out = []
    br = p.if_.one('a', out).continue_.if_.endif.endif
    assert br.is_ok
    assert out == ['a']
    assert p.pos == 1
    assert p._lookahead_stack == []

def test_break_does_not_backtrack_but_stops_expression():
    p = Parser("abc")
    out = []
    r = p.if_.one('a', out).if_.one('b', out).break_.endif.endif
    # Consumed 'a','b' (committed), position advanced
    assert not r.is_ok
    assert out == ['a', 'b']
    assert p.pos == 2
    assert p._lookahead_stack == []

def test_continue_end_state_returns_end():
    p = Parser("")
    p.end
    e = p.continue_
    assert e.is_ok
    assert isinstance(e, Parser.End)

def test_continue_behaves_like_break_but_true():
    p = Parser("abc")
    out = []
    r = p.if_.one('a', out).if_.one('b', out).continue_.endif.endif
    assert r.is_ok
    assert out == ['a', 'b']
    assert p.pos == 2
    assert p._lookahead_stack == []





def test_commit_keeps_consumption():
    p = Parser('a3!')
    l = []
    is_ok = p.lookahead.one('a', l).commit.is_ok
    assert is_ok
    assert l == ['a']
    assert p.pos == 1
    assert p._lookahead_stack == []


def test_is_backtrackable():
    p = Parser('a3!')
    l = []
    assert p.lookahead.one('a', l).is_backtrackable
    assert p.one('3', l).commit
    assert not p.is_backtrackable
    assert l == ['a', '3']

def test_lookahead_fail():
    p = Parser('a3!')
    l = []
    is_ok = p.lookahead.one('x', l).backtrack.is_ok
    assert not is_ok
    assert l == []
    assert p.pos == 0
    assert p._lookahead_stack == [0]


def test_nested_lookahead_with_alt_three_options_a_b_c():
    # Pattern: try 'a', else try 'b' in nested lookahead, else 'c' plain
    # a-path
    p = Parser('a.!')
    l = []
    is_ok = (
        p.lookahead.one('a', l)
         .alt
            .lookahead.one('b', l)
            .alt.one('c', l)
            .merge
        .merge
        .is_ok
    )
    assert is_ok and l == ['a'] and p.pos == 1 and p._lookahead_stack == []

    # b-path
    p = Parser('b.!')
    l = []
    is_ok = (
        p.lookahead.one('a', l)
         .alt
            .lookahead.one('b', l)
            .alt.one('c', l)
            .merge
        .merge
        .is_ok
    )
    assert is_ok and l == ['b'] and p.pos == 1 and p._lookahead_stack == []

    # c-path
    p = Parser('c.!')
    l = []
    is_ok = (
        p.lookahead.one('a', l)
         .alt
            .lookahead.one('b', l)
            .alt.one('c', l)
            .merge
        .merge
        .is_ok
    )
    assert is_ok and l == ['c'] and p.pos == 1 and p._lookahead_stack == []

    # None of 'a', 'b', 'c' match -> fatal, backtrack to 0, stack clean after merge
    p = Parser('q.!')
    l = []
    is_ok = (
        p.lookahead.one('a', l)
         .alt
            .lookahead.one('b', l)
            .alt.one('c', l)
            .merge
        .merge
        .is_ok
    )
    assert not is_ok
    assert l == []
    assert p.pos == 0
    assert p._lookahead_stack == []


def test_nested_alts_all_fail_backtrack_and_stack_clean():
    # Three nested lookaheads with alts; none match at any level -> fatal and full backtrack
    p = Parser('x')
    l = []
    is_ok = (
        p.lookahead.one('a', l)
         .alt
            .lookahead.one('b', l)
            .alt
                .lookahead.one('c', l)
                .alt.one('d', l)
                .merge
            .merge
        .merge
        .is_ok
    )
    assert not is_ok
    assert l == []
    assert p.pos == 0
    assert p._lookahead_stack == []


@pytest.mark.parametrize(
    "src, expected_l, expected_pos, expected_ok",
    [
        ("a1xy", ["a", '1', 'x', 'y'],   4, True), # first branch wins
        ("a1xz", ["a", "1", "x", "z"],   4, True), # z path
        ("a1xJ", ["a", "1", "x", "J"],   4, True), # J path

        # Main branch: LA1 = '1', LA2 alt = '2'
        ("a1K",  ["a", "1", "K"],        3, True),

        # Main branch: LA1 = '2', LA2 main = 'x', LA3 = 'y'/'z'/'Z'
        ("a2xy", ["a", "2", "x", "y"],   4, True),
        ("a2xz", ["a", "2", "x", "z"],   4, True),
        ("a2xJ", ["a", "2", "x", "J"],   4, True),

        # Main branch: LA1 = '2', LA2 alt = '2'
        ("a2K", ["a", "2", "K"],         3, True),

        # Outer alt branch successes: 'b' | 'c' | 'd'
        ("b1",   ["b"],                  1, True),
        ("cY",   ["c"],                  1, True),
        ("dZ",   ["d"],                  1, True),

        # New: successes of outer alts at EOF (cover commit on lookahead branches too)
        ("b",    ["b"],                  1, True),
        ("c",    ["c"],                  1, True),
        ("d",    ["d"],                  1, True),

        # Failures: main branch fails and outer alts don't match -> fatal
        ("a",    ["a"],                  0, False),  # EOF after 'a' before LA1
        ("a1",   ["a", "1"],             0, False),  # EOF before LA2 ('x'|'K')
        ("a2",   ["a", "2"],             0, False),  # EOF before LA2 ('x'|'K')
        ("a1x",  ["a", "1", "x"],        0, False),  # EOF before LA3 ('y'|'z'|'J')
        ("a2x",  ["a", "2", "x"],        0, False),  # EOF before LA3 ('y'|'z'|'J')

        ("a9",   ["a"],                  0, False),  # LA1 fails ('1'/'2' expected)
        ("aK",   ["a"],                  0, False),  # LA1 fails; outer alts don't match

        ("a1q",  ["a", "1"],             0, False),  # LA2 fails ('x' or '2' expected)
        ("a2q",  ["a", "2"],             0, False),  # LA2 fails after LA1='2'
        ("a1y",  ["a", "1"],             0, False),  # 'y' cannot appear before 'x'
        ("a2y",  ["a", "2"],             0, False),  # 'y' cannot appear before 'x'
        ("a1J",  ["a", "1"],             0, False),  # 'J' cannot appear before 'x'
        ("a2J",  ["a", "2"],             0, False),  # 'J' cannot appear before 'x'

        ("a1x?", ["a", "1", "x"],        0, False),  # LA3 fails (neither y/z/Z)
        ("a2x?", ["a", "2", "x"],        0, False),  # LA3 fails after LA1='2'
        ("q",    [],                     0, False),  # none of outer alternatives match
        ("a22",  ["a", "2"],             0, False),
    ],
)
def test_nested_deep(src, expected_l, expected_pos, expected_ok):
    p = Parser(src)
    l = []
    is_ok = (
        p.lookahead
            .one('a', l) # a
            .lookahead
                .one('1', l) # a1
            .alt
                .one('2', l) # a2
            .merge
            .lookahead
                .one('x', l) # a1x OR a2x
                .lookahead
                    .one('y', l) # a1xy OR a2xy
                .alt
                    .lookahead
                        .one('z', l) # a1xz OR a2xz
                    .alt
                        .one('J', l) # a1xJ OR a2xJ
                    .merge
                .merge
            .alt
                .one('K', l) # a1K OR a2K
            .merge
         .alt
            .lookahead
                .one('b', l) # b
            .alt
                .lookahead
                    .one('c', l) # c
                .alt
                    .one('d', l) # d
                .merge
            .merge
         .merge
        .is_ok
    )
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []



# -----------------------------------------------------------------------------
# fail / fail_if


def test_fail_basic():
    p = Parser("abc")
    start_pos = p.pos
    start_stack = list(p._lookahead_stack)
    f = p.fail
    assert not f.is_ok
    assert p.pos == start_pos
    assert p._lookahead_stack == start_stack

def test_fail_chaining_no_progress():
    p = Parser("abc")
    pos0 = p.pos
    f = p.fail.one('a')  # one() should be ignored because Fail.__getattr__ returns self
    assert not f.is_ok
    assert p.pos == pos0  # no consumption

def test_fail_after_end_state_and_idempotent():
    p = Parser("abc")
    p.end
    assert p.is_end_state
    e1 = p.fail
    assert e1.is_ok  # End.is_ok True
    e2 = e1.fail  # chaining on End returns End again
    assert e2 is e1

def test_fail_if_non_callable_true_false():
    p1 = Parser("ab")
    f = p1.fail_if(True)
    assert not f.is_ok
    p2 = Parser("ab")
    r = p2.fail_if(False)
    assert r.is_ok
    assert r.pos == 0

def test_fail_if_callable_true():
    p = Parser("xyz")
    def pred(a, b=None): return a == b
    f = p.fail_if(pred, 'x', b='x')
    assert not f.is_ok
    assert p.pos == 0

def test_fail_if_callable_false():
    p = Parser("xyz")
    def pred(a, b=None): return a == b
    r = p.fail_if(pred, 'x', b='z')
    assert r.is_ok
    assert p.pos == 0

def test_fail_if_callable_side_effect_not_called_in_end_state():
    p = Parser("a")
    called = []
    def pred():
        called.append(1)
        return False
    p.fail_if(pred)
    assert called == [1]
    p.end
    def boom():
        raise AssertionError("Should not be called")
    r = p.fail_if(boom)
    assert r.is_ok  # End
    assert called == [1]  # no extra call

def test_fail_if_inside_lookahead_peek_behavior():
    p = Parser("a!")
    l = []
    ok = p.lookahead.one('a', l).fail_if(True).alt.merge.is_ok
    assert ok
    # Peek: side effect retained, input not consumed
    assert l == ['a']
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_fail_property_inside_lookahead_peek_behavior():
    p = Parser("a!")
    l = []
    ok = p.lookahead.one('a', l).fail.alt.merge.is_ok
    assert ok
    assert l == ['a']
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_fail_if_false_inside_lookahead_commits():
    p = Parser("a!")
    l = []
    ok = p.lookahead.one('a', l).fail_if(False).commit.is_ok
    assert ok
    assert l == ['a']
    assert p.pos == 1
    assert p._lookahead_stack == []

def test_fail_if_true_without_alt_results_failed_branch_then_manual_backtrack():
    p = Parser("ab")
    p.lookahead.one('a')
    br = p.fail_if(True)
    assert not br.is_ok
    # Stack still has the saved pos (0)
    assert p._lookahead_stack == [0]
    # Manual backtrack from parser (access via parent) restores position
    p.backtrack()
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_fail_if_duplicate_side_effects_in_alt():
    p = Parser("aX")
    l = []
    ok = p.lookahead.one('a', l).fail_if(True).alt.one('a', l).merge.is_ok
    assert ok
    assert l == ['a', 'a']
    assert p.pos == 1

def test_fail_if_truthiness_variations():
    p1 = Parser("x")
    # Empty list predicate -> False -> pass
    r1 = p1.fail_if([])
    assert r1.is_ok
    p2 = Parser("x")
    # Non-empty list predicate -> True -> fail
    r2 = p2.fail_if([1])
    assert not r2.is_ok

def test_fail_if_callable_with_args_kwargs_and_side_effect():
    p = Parser("data")
    calls = []
    def pred(a, b, flag=False):
        calls.append((a, b, flag))
        return a == b and flag
    # Should be False (flag False) -> no fail
    r1 = p.fail_if(pred, 'x', 'x', flag=False)
    assert r1.is_ok
    # Should be True (all match) -> fail
    r2 = p.fail_if(pred, 'y', 'y', flag=True)
    assert not r2.is_ok
    assert calls == [('x', 'x', False), ('y', 'y', True)]

def test_fail_if_does_not_consume_on_failure():
    p = Parser("abc")
    f = p.fail_if(True)
    assert not f.is_ok
    assert p.pos == 0


# -----------------------------------------------------------------------------
# check



def test_check_callable_truthy():
    p = Parser("abc")
    r = p.check(lambda: True)
    assert r is p
    assert r.is_ok
    assert p.pos == 0
    assert p._lookahead_stack == []


def test_check_callable_falsy():
    p = Parser("abc")
    r = p.check(lambda: 0)  # falsy
    assert not r.is_ok
    assert isinstance(r, Parser.Fail)
    assert p.pos == 0
    assert p._lookahead_stack == []


def test_check_with_val_truthy():
    v = Parser.Val("abc")
    p = Parser("zzz")
    r = p.check(v, str.upper)  # v -> "ABC" (truthy)
    assert r is p and r.is_ok
    assert v.v == "ABC"
    assert p.pos == 0


def test_check_with_val_falsy_transform():
    v = Parser.Val("abc")
    p = Parser("zzz")
    r = p.check(v, lambda s: "")  # becomes '', falsy
    assert not r.is_ok
    assert v.v == ""
    assert p.pos == 0


def test_check_with_val_initial_falsy():
    v = Parser.Val("")  # already falsy
    p = Parser("x")
    r = p.check(v, lambda s: s)  # stays ''
    assert not r.is_ok
    assert v.v == ""


def test_check_fail_chain_does_not_consume():
    p = Parser("a")
    f = p.check(lambda: False).one('a')  # one ignored on Fail
    assert not f.is_ok
    assert p.pos == 0  # no consumption
    assert p.ch == 'a'


def test_check_in_lookahead_then_alt_branch():
    p = Parser("ba")
    out = []
    is_ok = (
        p.lookahead
          .one('a', out)            # fails to be used finally
          .check(lambda: False)     # force branch failure
          .alt
          .one('b', out)            # alt branch matches
          .merge
          .is_ok
    )
    assert is_ok
    assert out == ['b']
    assert p.pos == 1
    assert p._lookahead_stack == []


def test_check_fail_inside_lookahead_manual_backtrack():
    p = Parser("ax")
    p.lookahead.one('a')
    br = p.check(lambda: False)
    assert not br.is_ok
    # Stack still has saved pos
    assert p._lookahead_stack == [0]
    p.backtrack()
    assert p.pos == 0
    assert p._lookahead_stack == []


def test_check_tracing_truthy_and_falsy():
    p1 = Parser("abc")
    r1 = p1.check(lambda: True)
    assert r1.is_ok

    with trace_level(0) as traceable:
        if traceable:
            assert Parser._tracer is not None

            p_no_trace = Parser("abc")
            r1 = p_no_trace.check(lambda: True)
            assert r1.is_ok

    p2 = Parser("abc")
    r2 = p2.check(lambda: False)
    assert not r2.is_ok


def test_check_return_objects_independence():
    p = Parser("abc")
    fail_branch = p.check(lambda: False)
    assert isinstance(fail_branch, Parser.Fail)
    # Subsequent independent parsing still works
    ok = p.one('a').is_ok
    assert ok
    assert p.pos == 1
