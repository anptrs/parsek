""" Helpers for tests. """
from contextlib import contextmanager
from parsek import Parser

@contextmanager
def trace_level(level=0, **kwargs):
    """
    Temporarily set Parser tracing to the given level, then restore the previous state.
    Usage:
        with trace_level(0) as is_traceable:
            ...
    """
    if Parser.is_traceable():
        prev = Parser.set_trace(level=level, **kwargs)
        try:
            yield True
        finally:
            Parser.set_trace(*prev)
    else:
        yield False  # tracing not available
