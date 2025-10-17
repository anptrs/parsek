""" Test Parser if/elif/else/endif branching """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
import pytest
from parsek import Parser

def test_if_endif():
    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('!').do(l.append, 'no !').endif.is_ok
    assert l == []
    assert is_ok
    assert p.pos == 0
    assert not p.is_end
    assert p._lookahead_stack == []

    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('!').do(l.append, 'no !').endif.one('a', l).is_ok
    assert l == ['a']
    assert is_ok
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('a').do(l.append, 'a !').endif.is_ok
    assert l == ['a !']
    assert is_ok
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('a').do(l.append, 'a !').endif.one('3', l).is_ok
    assert l == ['a !', '3']
    assert is_ok
    assert p.pos == 2
    assert not p.is_end
    assert p._lookahead_stack == []


def test_if_else():
    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('!').do(list.append, l, 'no !').else_.one('a', l).endif.is_ok
    assert l == ['a']
    assert is_ok
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('a').do(list.append, l, 'yes a').else_.one('3', l).endif.is_ok
    assert l == ['yes a']
    assert is_ok
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('x').do(list.append, l, 'yes x').else_.one('y', l).endif.is_ok
    assert l == []
    assert not is_ok
    assert p.pos == 0
    assert not p.is_end
    assert p._lookahead_stack == []

def test_if_elif_else():
    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('!', l).elif_.one('3', l).else_.one('a', l).endif.is_ok
    assert is_ok
    assert l == ['a']
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('!', l).elif_.one('a', l).else_.one('3', l).endif.is_ok
    assert is_ok
    assert l == ['a']
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('!', l).else_.one('3', l).endif.is_ok
    assert is_ok
    assert l == ['a']
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    # fail:
    p = Parser('f3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('!', l).else_.one('3', l).endif.is_ok
    assert not is_ok
    assert l == []
    assert p.pos == 0
    assert not p.is_end
    assert p._lookahead_stack == []

    # no fail if elif instead of else:
    p = Parser('f3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('!', l).elif_.one('3', l).endif.is_ok
    assert is_ok
    assert l == []
    assert p.pos == 0
    assert not p.is_end
    assert p._lookahead_stack == []

    # no fail, last elif matches
    p = Parser('x3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('!', l).elif_.one('x', l).endif.one('3!', l).is_ok
    assert is_ok
    assert l == ['x', '3!']
    assert p.pos == 3
    assert p.is_end
    assert p._lookahead_stack == []


def p_if_nested(s):
    p = Parser(s)
    l = []
    b = p.Val()
    return p.if_.one('[').zero_or_more('1', result=b).\
                if_.one(p.END_CHAR).do(l.append, 'END - nested').\
                else_.one(']').do(l.append, b).endif.\
            elif_.one(p.END_CHAR).do(l.append, 'END').end.\
            else_.do(l.append, 'ELSE - last').endif, l


def test_if_nested():
    p, l = p_if_nested('a3!')
    print(l)
    assert p.is_ok
    assert l == ['ELSE - last']


def test_nested_if_in_true_branch():
    # Inner if matches
    p = Parser('a3!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'a')
            .if_.one('3').do(l.append, '3') #
            .else_.one('x').do(l.append, 'x')
            .endif
        .endif
        .is_ok
    )
    assert is_ok
    assert l == ['a', '3']
    assert p.pos == 2
    assert not p.is_end
    assert p._lookahead_stack == []

    # Inner else matches
    p = Parser('ax!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'a')
            .if_.one('3').do(l.append, '3')
            .else_.one('x').do(l.append, 'x')
            .endif
        .endif
        .is_ok
    )
    assert is_ok
    assert l == ['a', 'x']
    assert p.pos == 2
    assert not p.is_end
    assert p._lookahead_stack == []

    # Inner if and else both fail -> entire outer lookahead fails and backtracks
    p = Parser('a?!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'a')
            .if_.one('3').do(l.append, '3')
            .else_.one('x').do(l.append, 'x')
            .endif
        .endif
        .is_ok
    )
    # Outer if fails because inner lookahead failed; side-effect 'a' still happened
    assert is_ok
    assert l == ['a']
    assert p.pos == 0
    assert not p.is_end
    assert p._lookahead_stack == []

    # Inner if and elif all fail -> outer ok, because inner has no else branch
    p = Parser('a?!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'a')
            .if_.one('3').do(l.append, '3')
            .elif_.one('x').do(l.append, 'x')
            .endif
        .endif
        .is_ok
    )
    # Outer if fails because inner lookahead failed; side-effect 'a' still happened
    assert is_ok
    assert l == ['a']
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    # Inner if and elif and else all fail -> outer fails too
    p = Parser('a?!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'a')
            .if_.one('3').do(l.append, '3')
            .elif_.one('x').do(l.append, 'x')
            .else_.one('y').do(l.append, 'y')
            .endif
        .endif
        .is_ok
    )
    # Outer if fails because inner lookahead failed; side-effect 'a' still happened
    assert is_ok
    assert l == ['a']
    assert p.pos == 0
    assert not p.is_end
    assert p._lookahead_stack == []


def test_nested_outer_if_with_else_is_fatal_on_inner_failure():
    # Same setup as above, but add an outer else that also fails -> whole chain fails (is_ok == False)
    p = Parser('a?!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'a')
            .if_.one('3')          # inner if fails
            .else_.one('x')        # inner else fails
            .endif                 # => outer if branch fails
        .else_.one('!')            # outer else also fails (input back at pos 0: 'a?!')
        .endif
        .is_ok
    )
    assert not is_ok               # fatal when no outer branch matches (with else present)
    assert l == ['a']
    assert p.pos == 0
    assert p._lookahead_stack == []

def test_elif_chain_all_paths():
    # a-path
    p = Parser('a3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('b', l).elif_.one('c', l).else_.one('d', l).endif.is_ok
    assert is_ok and l == ['a'] and p.pos == 1 and p._lookahead_stack == []

    # b-path
    p = Parser('b3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('b', l).elif_.one('c', l).else_.one('d', l).endif.is_ok
    assert is_ok and l == ['b'] and p.pos == 1 and p._lookahead_stack == []

    # c-path
    p = Parser('c3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('b', l).elif_.one('c', l).else_.one('d', l).endif.is_ok
    assert is_ok and l == ['c'] and p.pos == 1 and p._lookahead_stack == []

    # else-path
    p = Parser('d3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('b', l).elif_.one('c', l).else_.one('d', l).endif.is_ok
    assert is_ok and l == ['d'] and p.pos == 1 and p._lookahead_stack == []

    # full-chain fails (no else match)
    p = Parser('x3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('b', l).elif_.one('c', l).else_.one('d', l).endif.is_ok
    assert not is_ok and l == [] and p.pos == 0 and p._lookahead_stack == []

    # full-chain fails but parser is still in a valid state elif replaces else:
    p = Parser('x3!')
    l = []
    is_ok = p.if_.one('a', l).elif_.one('b', l).elif_.one('c', l).elif_.one('d', l).endif.is_ok
    assert is_ok and l == [] and p.pos == 0 and p._lookahead_stack == []

def test_nested_if_inside_else_branch():
    # Outer if fails, nested chain inside else picks 'b'
    p = Parser('b3!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'A')
         .else_
            .if_.one('b').do(l.append, 'B')
            .elif_.one('c').do(l.append, 'C')
            .else_.one('x').do(l.append, 'X')
            .endif
        .endif
        .is_ok
    )
    assert is_ok
    assert l == ['B']
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    # Outer if fails, nested chain inside else fails entirely
    p = Parser('z3!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'A')
         .else_
            .if_.one('b').do(l.append, 'B')
            .elif_.one('c').do(l.append, 'C')
            .endif
        .endif
        .is_ok
    )
    assert is_ok
    assert l == []
    assert p.pos == 0
    assert not p.is_end
    assert p._lookahead_stack == []


def test_deeply_nested_multiple_levels():
    # Build a small decision tree:
    # if 'a': record 'A'
    #    if '3': record 'A3'
    #    elif '!': record 'A!'
    #    else: record 'A?'
    # elif 'b': record 'B'
    # else: record 'Z'
    p = Parser('a!x')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'A')
            .if_.one('3').do(l.append, 'A3')
            .elif_.one('!').do(l.append, 'A!')
            .else_.do(l.append, 'A?')
            .endif
        .elif_.one('b').do(l.append, 'B')
        .else_.do(l.append, 'Z')
        .endif
        .is_ok
    )
    assert is_ok
    assert l == ['A', 'A!']
    # consumed 'a' and '!' -> pos 2
    assert p.pos == 2
    assert not p.is_end
    assert p._lookahead_stack == []

    # b path
    p = Parser('b3!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'A')
            .if_.one('3').do(l.append, 'A3')
            .elif_.one('!').do(l.append, 'A!')
            .else_.do(l.append, 'A?')
            .endif
        .elif_.one('b').do(l.append, 'B')
        .else_.do(l.append, 'Z')
        .endif
        .is_ok
    )
    assert is_ok
    assert l == ['B']
    assert p.pos == 1
    assert not p.is_end
    assert p._lookahead_stack == []

    # default Z path
    p = Parser('x3!')
    l = []
    is_ok = (
        p.if_.one('a').do(l.append, 'A')
            .if_.one('3').do(l.append, 'A3')
            .elif_.one('!').do(l.append, 'A!')
            .else_.do(l.append, 'A?')
            .endif
        .elif_.one('b').do(l.append, 'B')
        .else_.do(l.append, 'Z')
        .endif
        .is_ok
    )
    assert is_ok
    assert l == ['Z']
    assert p.pos == 0  # else branch here only did a side-effect, did not consume input
    assert not p.is_end



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

        # Outer else branch successes: 'b' | 'c' | 'd'
        ("b1",   ["b"],                  1, True),
        ("cY",   ["c"],                  1, True),
        ("dZ",   ["d"],                  1, True),

        # Failures: main branch fails and outer else don't match -> fatal
        ("a9",   ["a"],                  0, False),  # LA1 fails ('1'/'2' expected)
        ("a1q",  ["a", "1"],             0, False),  # LA2 fails ('x' or '2' expected)
        ("a1x?", ["a", "1", "x"],        0, False),  # LA3 fails (neither y/z/Z)
        ("a2q",  ["a", "2"],             0, False),  # LA2 fails after LA1='2'
        ("a2x?", ["a", "2", "x"],        0, False),  # LA3 fails after LA1='2'
        ("q",    [],                     0, False),  # none of outer alternatives match
        ("a22",  ["a", "2"],             0, False),
    ],
)
def test_deep_nested(src, expected_l, expected_pos, expected_ok):
    p = Parser(src)
    l = []
    is_ok = (
        p.if_
            .one('a', l)
            .if_
                .one('1', l) # a1
            .else_
                .one('2', l) # a2
            .endif
            .if_
                .one('x', l) # a1x OR a2x
                .if_
                    .one('y', l) # a1xy OR a2xy
                .else_
                    .if_
                        .one('z', l) # a1xz OR a2xz
                    .else_
                        .one('J', l) # a1xJ OR a2xJ
                    .endif
                .endif
            .else_
                .one('K', l) # a1K OR a2K
            .endif
         .else_
            .if_
                .one('b', l) # b
            .else_
                .if_
                    .one('c', l) # c
                .else_
                    .one('d', l) # d
                .endif
            .endif
        .endif
        .is_ok
    )
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
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

        # Outer else branch successes: 'b' | 'c' | 'd'
        ("b1",   ["b"],                  1, True),
        ("cY",   ["c"],                  1, True),
        ("dZ",   ["d"],                  1, True),

        # Failures: main branch fails and outer else don't match -> fatal
        ("a9",   ["a"],                  0, False),  # LA1 fails ('1'/'2' expected)
        ("a1q",  ["a", "1"],             0, False),  # LA2 fails ('x' or '2' expected)
        ("a1x?", ["a", "1", "x"],        0, False),  # LA3 fails (neither y/z/Z)
        ("a2q",  ["a", "2"],             0, False),  # LA2 fails after LA1='2'
        ("a2x?", ["a", "2", "x"],        0, False),  # LA3 fails after LA1='2'
        ("q",    [],                     0, False),  # none of outer alternatives match
        ("a22",  ["a", "2"],             0, False),
    ],
)
def test_deep_nested_elif(src, expected_l, expected_pos, expected_ok):
    p = Parser(src)
    l = []
    is_ok = (
        p.if_
            .one('a', l)
            .if_
                .one('1', l) # a1
            .else_
                .one('2', l) # a2
            .endif
            .if_
                .one('x', l) # a1x OR a2x
                .if_
                    .one('y', l) # a1xy OR a2xy
                .elif_
                    .one('z', l) # a1xz OR a2xz
                .else_
                    .one('J', l) # a1xJ OR a2xJ
                .endif
            .else_
                .one('K', l) # a1K OR a2K
            .endif
         .else_
            .if_
                .one('b', l) # b
            .elif_
                .one('c', l) # c
            .else_
                .one('d', l) # d
            .endif
        .endif
        .is_ok
    )
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []



@pytest.mark.parametrize(
    "src, expected_l, expected_pos, expected_ok",
    [
        ("a1xy", ["a", '1'],             0, False), # a1... always false because break_

        # Main branch: LA1 = '2', LA2 main = 'x', LA3 = 'y'/'z'/'Z'
        ("a2xy", ["a", "2", "x", "y"],   0, False),
        ("a2xz", ["a", "2", "x", "z"],   4, True),
        ("a2xJ", ["a", "2", "x", "J"],   0, False),

        # Main branch: LA1 = '2', LA2 alt = '2'
        ("a2K", ["a", "2", "K"],         3, True),

        # Outer else branch successes: 'b' | 'c' | 'd'
        ("b1",   ["b"],                  0, False),
        ("cY",   ["c"],                  0, False),
        ("dZ",   ["d"],                  1, False),

        # Failures: main branch fails and outer else don't match -> fatal
        ("a9",   ["a"],                  0, False),  # LA1 fails ('1'/'2' expected)
        ("a1q",  ["a", "1"],             0, False),  # LA2 fails ('x' or '2' expected)
        ("a1x?", ["a", "1"],             0, False),  # LA3 fails (neither y/z/Z)
        ("a2q",  ["a", "2"],             0, False),  # LA2 fails after LA1='2'
        ("a2x?", ["a", "2", "x"],        0, False),  # LA3 fails after LA1='2'
        ("q",    [],                     0, False),  # none of outer alternatives match
        ("a22",  ["a", "2"],             0, False),
    ],
)
def test_deep_nested_back(src, expected_l, expected_pos, expected_ok):
    p = Parser(src)
    l = []
    is_ok = (
        p.if_
            .one('a', l)
            .if_
                .one('1', l) # a1
                .back
            .else_
                .one('2', l) # a2
            .endif
            .if_
                .one('x', l) # a1x OR a2x
                .if_
                    .one('y', l) # a1xy OR a2xy
                    .back
                .elif_
                    .one('z', l) # a1xz OR a2xz

                .else_
                    .one('J', l) # a1xJ OR a2xJ
                    .back
                .endif
            .else_
                .one('K', l) # a1K OR a2K
            .endif
         .else_
            .if_
                .one('b', l) # b
                .back
            .elif_
                .one('c', l) # c
                .back
            .else_
                .one('d', l) # d
                .back
            .endif
         .endif
        .is_ok
    )
    assert is_ok is expected_ok
    assert l == expected_l
    assert p.pos == expected_pos
    assert p._lookahead_stack == []
