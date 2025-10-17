""" Pytest configuration file """
import importlib
import sys
#import pytest

def pytest_addoption(parser):
    """ Add command line options to pytest """
    parser.addoption(
        "--parser-trace",
        action="store",
        type=int,
        default=None,
        help="Set Parser trace level (overrides PARSER_TRACE_LEVEL env var)",
    )
    parser.addoption(
        "--use-parsek-min",
        action="store_true",
        default=False,
        help="Alias 'parsek' to 'parsek_min' for all imports during tests",
    )

def pytest_configure(config):
    """Early configuration: possibly swap the module and set trace before collection."""
    mini = False
    if config.getoption("--use-parsek-min"):
        mini = True
        mod = importlib.import_module("parsek_min")
        sys.modules["parsek"] = mod

    try:
        Parser = getattr(importlib.import_module("parsek"), "Parser") # pylint: disable=invalid-name
    except Exception: # pylint: disable=broad-except
        Parser = None # pylint: disable=invalid-name

    # set trace level:
    if not mini:
        lvl = config.getoption("--parser-trace")
        if lvl is None:
            lvl = 3
        if Parser and lvl is not None:
            Parser.set_trace(lvl)

# @pytest.fixture(autouse=True, scope="session")
# def _parser_trace(request):
#     lvl = request.config.getoption("--parser-trace")
#     if lvl is None:
#         lvl = 3
#     if lvl is not None:
#         Parser.set_trace(lvl) # OK
