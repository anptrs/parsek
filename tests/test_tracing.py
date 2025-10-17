""" Test Parser tracing features. """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison,unnecessary-lambda-assignment
from parsek import Parser

def test_set_trace(): # OK
    if Parser.is_traceable():
        prev_trace  = Parser._trace
        Parser.set_trace(0) # disable OK: TEST
        assert not Parser._trace
        got = Parser.set_trace(3) # enable OK: TEST
        assert got == (0, True, print)
        assert Parser._trace == (3, True, print)
        if prev_trace is not None:
            Parser.set_trace(*prev_trace) # restore OK: TEST
        else:
            Parser.set_trace(0) # disable OK: TEST

def test_trace_out(monkeypatch):
    if Parser.is_traceable():
        prev_trace  = Parser._trace
        # Ensure tracer initialized so Parser._tracer exists
        l_out = []
        Parser.set_trace(level=1, color=False, out=l_out.append) # OK: TEST
        assert Parser._tracer is not None

        p = Parser("hello world")
        # IMPORTANT: If the following line moves up or down in this source then adjust the expected output!
        p._trace_out(1, False, l_out.append, "Test msg")
        print(l_out)
        assert l_out == ['1                                          test_trace_out:0028   Test msg']
        l_out.clear()

        # IMPORTANT: If the following line moves up or down in this source then adjust the expected output!
        def nest_func():
            p._trace_out(2, False, l_out.append, "Test msg nested")
        nest_func()
        print(l_out)
        assert l_out == ['2                                               nest_func:0035   Test msg nested']
        l_out.clear()

        # Monkeypatch inspect_.stack to simulate no-stack situation
        def no_stack():
            return None
        monkeypatch.setattr(Parser._tracer.inspect_, "stack", no_stack)

        p._trace_out(1, False, l_out.append, "Test msg 2")
        print(l_out)
        assert l_out == ['1: Test msg 2']
        l_out.clear()

        # Monkeypatch inspect_.stack to simulate exception situation
        def boom():
            raise Exception("no stack") # pylint: disable=broad-exception-raised
        monkeypatch.setattr(Parser._tracer.inspect_, "stack", boom)

        p._trace_out(1, False, l_out.append, "Test msg 3")
        print(l_out)
        assert l_out == ['1: Test msg 3']


        if prev_trace is not None:
            Parser.set_trace(*prev_trace) # restore OK: TEST
        else:
            Parser.set_trace(0) # disable OK: TEST


def test_lambdas():
    if Parser.is_traceable():
        prev_trace  = Parser._trace
        # Ensure tracer initialized so Parser._tracer exists
        Parser.set_trace(level=1) # OK: TEST
        assert Parser._tracer is not None
        l = Parser._lambdas("  if p.if_.one('lambda :').do(print, \"my lambda x: ...\").one(lambda x=[(h+5, \"hi: \", k[1:5])] : x + 3)")
        assert l == [ (('x',), 'x + 3') ]

        if prev_trace is not None:
            Parser.set_trace(*prev_trace) # restore OK: TEST
        else:
            Parser.set_trace(0) # disable OK: TEST


def test_lambda(monkeypatch):
    if Parser.is_traceable():
        prev_trace  = Parser._trace
        # Ensure tracer initialized so Parser._tracer exists
        Parser.set_trace(level=1) # OK: TEST
        assert Parser._tracer is not None

        # Monkeypatch getsourcelines to simulate failure
        def boom(_f):
            return ["  if p.if_.one('lambda :').do(print, \"my lambda x: ...\").one(lambda x=[(h+5, \"hi: \", k[1:5])] : x + 3)"], 3456
        monkeypatch.setattr(Parser._tracer.inspect_, "getsourcelines", boom)

        fn = lambda x: x  # any lambda
        name = Parser._f_name(fn)  # will call Parser._lambda internally
        assert name == "λ₃₄₅₆ x: x + 3"
        if prev_trace is not None:
            Parser.set_trace(*prev_trace) # restore OK: TEST
        else:
            Parser.set_trace(0) # disable OK: TEST


def test_lambda_no_source(monkeypatch):
    if Parser.is_traceable():
        prev_trace  = Parser._trace
        # Ensure tracer initialized so Parser._tracer exists
        Parser.set_trace(level=1) # OK: TEST
        assert Parser._tracer is not None

        # Monkeypatch getsourcelines to simulate failure
        def boom(_f):
            raise OSError("no source")
        monkeypatch.setattr(Parser._tracer.inspect_, "getsourcelines", boom)

        fn = lambda x: x  # any lambda
        name = Parser._f_name(fn)  # will call Parser._lambda internally
        assert name == "λ"  # falls back to plain lambda symbol on exception
        if prev_trace is not None:
            Parser.set_trace(*prev_trace) # restore OK: TEST
        else:
            Parser.set_trace(0) # disable OK: TEST

def test_lambda_bad_source(monkeypatch):
    if Parser.is_traceable():
        prev_trace  = Parser._trace
        # Ensure tracer initialized so Parser._tracer exists
        Parser.set_trace(level=1) # OK: TEST
        assert Parser._tracer is not None

        # Monkeypatch getsourcelines to simulate None source
        def boom(_f):
            return None, 0
        monkeypatch.setattr(Parser._tracer.inspect_, "getsourcelines", boom)

        fn = lambda x: x  # any lambda
        name = Parser._f_name(fn)  # will call Parser._lambda internally
        assert name == "λ₀"  # falls back to plain lambda symbol on exception

        # Monkeypatch getsourcelines to simulate [] source
        def boom2(_f):
            return [], 0
        monkeypatch.setattr(Parser._tracer.inspect_, "getsourcelines", boom2)

        fn2 = lambda x: x  # any lambda
        name = Parser._f_name(fn2)  # will call Parser._lambda internally
        assert name == "λ₀"  # falls back to plain lambda symbol on exception


        if prev_trace is not None:
            Parser.set_trace(*prev_trace) # restore OK: TEST
        else:
            Parser.set_trace(0) # disable OK: TEST

def test_lambda_bad_lineno(monkeypatch):
    if Parser.is_traceable():
        prev_trace  = Parser._trace
        # Ensure tracer initialized so Parser._tracer exists
        Parser.set_trace(level=1) # OK: TEST
        assert Parser._tracer is not None

        # Monkeypatch getsourcelines to simulate failure
        def boom(_f):
            return None, None
        monkeypatch.setattr(Parser._tracer.inspect_, "getsourcelines", boom)

        fn = lambda x: x  # any lambda
        name = Parser._f_name(fn)  # will call Parser._lambda internally
        assert name == "λ₀"  # falls back to plain lambda symbol on exception
        if prev_trace is not None:
            Parser.set_trace(*prev_trace) # restore OK: TEST
        else:
            Parser.set_trace(0) # disable OK: TEST
