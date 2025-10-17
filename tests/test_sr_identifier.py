""" Test for Parser.identifier subroutine """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# pylint: disable=broad-exception-raised
import pytest
from parsek import Parser



@pytest.mark.parametrize(
    "src, expected_val, expected_pos, expected_ok",
    #  0         1         2         3         4         5         6
    #  012345678901234567890123456789012345678901234567890123456789012
    [(" hello ", 'hello', 6, True),
     (" _abc ", '_abc', 5, True),
     (" _abc123 ", '_abc123', 8, True),
     (" _123 ", '_123', 5, True),
     ("_ ", '_', 1, True),
     ("_", '_', 1, True),
     ("_z ", '_z', 2, True),
     ("_z", '_z', 2, True),
     (" 12", None, 1, False),
     ("  ", None, 2, False),
     ("", None, 0, False),
    ]
)
def test_identifier(src, expected_val, expected_pos, expected_ok):
    """ Tests the identifier subroutine."""
    p = Parser(src)
    l = []
    expected_val = [] if expected_val is None else [expected_val]

    is_ok = p.ws.one(p.identifier, l).is_ok
    assert is_ok is expected_ok
    assert l == expected_val
    assert p.pos == expected_pos
    assert p._lookahead_stack == []
