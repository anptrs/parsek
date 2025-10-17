""" Test different parsers """
# pylint: disable=protected-access,missing-function-docstring,line-too-long,multiple-statements,use-implicit-booleaness-not-comparison
# cspell:words dlrusz,lambd,uppe,sdfs,docstrings,ebnf,jvalue,jkey,qchar,qcontent,e̲xtra
import re
from textwrap import dedent, indent as indent_text
import pytest
from parsek import Parser, Val, Not, In, add_static


def test_parse_style_str():
    # [...] segment segment ... [...] segment ...
    #    0         1         2         3         4         5         6
    #    01234567890123456789012345678901234567890123456789012345678901234567890
    s = '[red,b] <r5> l7 " te\\\"xt " [] s ! z> [/blue] z s1 z0> !0 ~l6 ~u-2 '
    #           ^    ^                    ^          ^    ^      ^
    p = Parser(s)
    r = []

    def is_cap(ch):
        return ch not in (' \n\t!~dlrusz\'"')

    @p.subroutine
    def style(p:Parser):
        result = Parser.Val('')
        return p.one('[').zero_or_more(p.Not(p.In(']')), result).one(']').do(list.append, r, result.value).is_ok

    @p.subroutine
    def segment(p:Parser):
        d = {'type': 'seg'}
        return p.zero_or_more(is_cap, (d, 'bc')).zero_or_one('~', (d, 'm')).one(('d','l','r','u'), (d, 'd')).\
            one(p.decimal, (d, 'l')).zero_or_more(is_cap, (d, 'ec')).do(list.append, r, d).is_ok

    @p.subroutine
    def other(p:Parser):
        d_text = {'type': 'text'}
        d_z = {'type': 'z'}
        d_sp = {} # s or !
        return p.  if_.one(p.string, (d_text, 'v')).do(list.append, r, d_text).\
                   elif_.zero_or_more(is_cap, (d_z, 'bc')).one('z').\
                       zero_or_one(p.uint, (d_z, 'n')).zero_or_more(is_cap, (d_z, 'ec')).do(list.append, r, d_z).\
                   else_.one(('s', '!'), (d_sp, 'type')).zero_or_one(p.int_, (d_sp, 'n')).do(r.append, d_sp).\
                   endif.is_ok

    @p.subroutine
    def token(p:Parser):
        return p.ws.if_.one(p.END_CHAR).end.endif.\
            if_.one(style).elif_.one(segment).else_.one(other).endif.is_ok

    is_ok = p.zero_or_more(token).ws.one(p.END_CHAR, nomatch='Unexpected path element').is_ok
    # print(r)
    print('\n'.join(str(i) for i in r))
    assert p._lookahead_stack == [] # pylint: disable=protected-access
    assert is_ok
    assert p.is_end
    assert p.is_past_end
    assert r == ['red,b', {'type': 'seg', 'bc': '<', 'd': 'r', 'l': 5, 'ec': '>'},
                 {'type': 'seg', 'd': 'l', 'l': 7}, {'type': 'text', 'v': ' te"xt '}, '',
                 {'type': 's'}, {'type': '!'}, {'type': 'z', 'ec': '>'}, '/blue', {'type': 'z'},
                 {'type': 's', 'n': 1}, {'type': 'z', 'n': 0, 'ec': '>'}, {'type': '!', 'n': 0},
                 {'type': 'seg', 'm': '~', 'd': 'l', 'l': 6}, {'type': 'seg', 'm': '~', 'd': 'u', 'l': -2}]

@add_static('str_ch',  Not(In(Parser.END_CHAR + '[')))
@add_static('style_ch', Not(In(Parser.END_CHAR + ']')))
def split_styles(s: str):
    p = Parser(s)
    r = []

    @p.subroutine
    def escape(p, txt):
        # return p.if_.one('[[').do(txt.append, '[').zero_or_more(split_styles.str_ch, acc=txt).\
        #              zero_or_more(escape, txt).endif.is_ok
        return p.one('[[').do(txt.append, '[').zero_or_more(split_styles.str_ch, acc=txt).\
                     zero_or_more(escape, txt).is_ok

    @p.subroutine
    def text_or_style(p):
        txt = p.Val('')
        style = p.Val()

        if p.if_.zero_or_more(split_styles.str_ch, acc=txt).\
                 zero_or_more(escape, txt).\
             endif.\
             if_.one('[').zero_or_more(split_styles.style_ch, acc=style).\
                 if_.one(p.END_CHAR).do(txt.append,'[').do(txt.append, style.value).do(style.reset).\
                 else_.one(']').\
                 endif.\
             elif_.one(p.END_CHAR).end.\
             endif:
            if txt.value:
                r.append(txt.value)
            if style.is_str:
                r.append(style.value)
            print(f"style: {style.value}; txt: {txt.value}")
            return True
        return False

    _is_ok = p.zero_or_more(text_or_style).one(p.END_CHAR, nomatch='Unexpected style element').is_ok
    return r, p

def test_split_styles():
    #    0         1         2         3         4         5         6
    #    01234567890123456789012345678901234567890123456789012345678901234567890
    s = '[red,b] hello [[ world [[not a tag] [/b] [/red] bye [black '
    r, p = split_styles(s)
    print('IN :', s)
    print('OUT:', '\n'.join(r))
    assert r == ['red,b', ' hello [ world [not a tag] ', '/b', ' ', '/red', ' bye [black ']
    assert p.is_ok
    assert p._lookahead_stack == []

def test_split_styles_2():
    #    0         1         2         3         4         5         6
    #    01234567890123456789012345678901234567890123456789012345678901234567890
    s = '[red,b]'
    r, p = split_styles(s)
    print('IN :', s)
    print('OUT:', '\n'.join(r))
    assert r == ['red,b']
    assert p.is_ok
    assert p._lookahead_stack == []

def test_split_styles_3():
    #    0         1         2         3         4         5         6
    #    01234567890123456789012345678901234567890123456789012345678901234567890
    s = 'hello world'
    r, p = split_styles(s)
    print('IN :', s)
    print('OUT:', '\n'.join(r))
    assert r == ['hello world']
    assert p.is_ok
    assert p._lookahead_stack == []

def test_split_styles_empty():
    #    0         1         2         3         4         5         6
    #    01234567890123456789012345678901234567890123456789012345678901234567890
    s = ''
    r, p = split_styles(s)
    print('IN :', s)
    print('OUT:', '\n'.join(r))
    assert r == []
    assert p.is_ok
    assert p._lookahead_stack == []


def get_tag(text: str)-> str:
    if Parser(text).x0_(Parser.chars('^<$')).x1('<').x1_(Parser.chars('^>$'), tag := Val()).x1('>'):
        return tag.value
    raise ValueError("No tag found")

def test_get_tag():
    assert get_tag('  some text <hello> more text') == 'hello'
    assert get_tag('<tag>') == 'tag'
    assert get_tag('prefix <a b c> suffix') == 'a b c'
    with pytest.raises(ValueError, match="No tag found"):
        get_tag('no tag here')
    with pytest.raises(ValueError, match="No tag found"):
        get_tag('almost <tag but no close')
    with pytest.raises(ValueError, match="No tag found"):
        get_tag('> no open tag here')



def parse_lambda_body(s):
    p = Parser(s)
    brackets = {'(':')', '[':']', '{':'}', None: None}

    @p.subroutine
    def br(p: Parser, bc):
        closed = Val(False)
        while p.is_active and (p.zero_or_more(p.chars('^([{}])\'"#$')).
            if_.one(In('([{'), b := Val()).one(br, brackets[b]).
            elif_.one(bc, closed).break_.
            elif_.one(p.string).
            else_.end.endif): pass
        return closed

    while p.is_active and (p.zero_or_more(p.chars('^,([{}])\'"#$')).
        if_.one(In('([{'), b := Val()).one(br, brackets[b]).
        elif_.one(p.string).
        else_.end.endif): pass
    body = p.slice_from(0)
    print(f"Body: {body!r}")
    return body

@pytest.mark.parametrize("src, expected_val",
    [("x + 1,", "x + 1"),
     ("(x + 1)(y+2*(3 +4)) + \"(hello,\"", "(x + 1)(y+2*(3 +4)) + \"(hello,\""),
     ("(x + 1)(y+2*(3 +4)) + \"(hello,\"), (not body)", "(x + 1)(y+2*(3 +4)) + \"(hello,\""),
     ("(x + 1)(y+2*(3 +4)) + \"),(hello,\"), (not body)", "(x + 1)(y+2*(3 +4)) + \"),(hello,\""),
     ("[(x+1), y+2], (not body)", "[(x+1), y+2]"),
    ])
def test_lambda_context(src, expected_val):
    assert parse_lambda_body(src) == expected_val


def parse_lambda(s):
    # looks for the start of a lambda body declaration: "lambda x: ..." or "(lambda x=[(h+5, "hi: ",)] : ...)"
    p = Parser(s)
    brackets = {'(':')', '[':']', '{':'}'} #, None: None}

    @p.subroutine
    def br(p: Parser, bc):
        closed = Val(False)
        while p.is_active and (p.x0_(p.chars('^([{}])\'"#$')).
            #if_.one(In('([{'), b := Result()).one(br, brackets[b]).
            if_.one(brackets, b := Val()).one(br, b).
            elif_.one(bc, closed).break_.
            elif_.one(p.string, on_err=None).else_.end.endif): pass
        return closed

    @p.subroutine
    def expr(p: Parser, out):
        pos = p.pos
        while p.is_active and (p.x0_(p.chars('^:,([{}])\'"#$')).
            # if_.one(In('([{'), b := Result()).one(br, brackets[b]).
            if_.one(brackets, b := Val()).one(br, b).
            elif_.one(p.string, on_err=None).else_.break_.endif): pass
        out.append(p.slice_from(pos).strip())
        print(f"expr: {out!r}")
        return True

    @p.subroutine
    def param(p: Parser, out, **_kwargs): # parse a single param terminated by , or :
        return p.ws.one(p.identifier, acc=out).ws.if_.one('=').ws.one(expr, Val()).endif

    @p.subroutine
    def lambda_def(p: Parser, out):
        found = Val(False)
        while p.is_active and (p.x0_(p.Not(('lambda', p.chars('\'"#$'),))).
        #while p.is_active and (p.x0_(p.Not(('"', "'", '#', 'lambda', p.END_CHAR))).
            if_.one('lambda').one(p.collection, param, out=(count := Val(0, lambda c, _: c+1)), brackets={None: ':'}, on_err=None).ws.
                one(expr, body := Val(), acc=found).do(out.append, (count.v, body.value)).break_.
            elif_.one(p.string, on_err=None).
            elif_.one(p.END_CHAR).end.
            else_.break_.endif): pass
        return found

    lambdas = [] # list of lambdas: [(param_count, body), ...]
    while p.is_active and p.x1_(lambda_def, lambdas): pass

    print(f"Lambdas: {lambdas}")
    return lambdas

@pytest.mark.parametrize("src, expected_val",
    [("p.one(\"lambda\", k).one(lambda ch: ch == 'x', r).is_ok", [(1, "ch == 'x'")]),
     ("p.one(\"lambda\", k).one(lambda ch: ch == 'x'  #comment, r).is_ok", [(1, "ch == 'x'")]),
     ("p.one(\"lambda ch: ...\", k).one(lambda ch, b=s[1:(3+4 +foo(1,2,3))]: ch != 'z', r).is_ok", [(2, "ch != 'z'")]),
     ("p.one(\"lambda ch: ...\", k).one(lambd ch: ch == 'a', r).is_ok", []),
     ("l1 = lambda s=k[:1]: s.upper() # valid lambda definition", [(1, "s.upper()")]),
     ("l1 = lambda s=k[:1]: s.uppe", [(1, 's.uppe')]),
     ("l1 = lambda s=k[:1]+(1 + 4): s.upper() # valid lambda definition", [(1, "s.upper()")]),
     ("p.one(lambda ch: ch == 'a', k).one(lambda ch, j: ch == 'b' an not j, r).is_ok", [(1, "ch == 'a'"), (2, "ch == 'b' an not j")]),
     ("l1 = lambda s=k[:1]+(1 + ", []),
     ("l1 = lambda s: ( 42 + ... ", [(1, '( 42 + ...')]),
     ("l1 = lambda s: ( 42 + z l2 = lambda : None", [(1, '( 42 + z l2 = lambda : None')]),
     ("l1 = lambda s: 'not closed ...", [(1, '')]),
     ("l1 = lambda s", []),
     (" do(lambda: print('.')).\n", [(0, "print('.')")]),
     ("  if p.if_.one('lambda :').do(print, \"my lambda x: ...\").one(lambda x=[(h+5, \"hi: \", k[1:5])] : x + 3)",
      [(1, 'x + 3')]),
     ("sdfs", []),
     ("", []),
("""\
    ok = p.x1_(name := p.sr(lambda p: (
        p.do(print, '.').x1_(p.chars('^=\n#;[] \t$')).
        if_.x1_(' \t').
            if_.one(']').back.else_.one(name).endif.
        endif))).is_ok
""", [(1, "(\n        p.do(print, '.').x1_(p.chars('^=\n#;[] \t$')).\n        if_.x1_(' \t').\n            if_.one(']').back.else_.one(name).endif.\n        endif)")]),
    ])
def test_parse_lambda(src, expected_val):
    assert parse_lambda(src) == expected_val


def remove_comments(s):
    # removes comments and docstrings from python source code
    p, out = Parser(s), []

    # parses out triple quote strings (not just docstrings), both '''...''' and """..."""
    # note this doesn't handle escapes so \``` will break it
    @p.sr
    def docstring(p: Parser):
        return p.one(('"""', "'''"), q := Val()).zero_or_more(Not(q)).one(q)

    while p.is_active and (
        p.x0_(p.chars('^\'"#$'), acc=out).
        if_.x1('#').x0_(p.chars('^\n$')).one('\n', out).
        elif_.x1(docstring).
        elif_.x1(p.string, acc=out).
        else_.x1(p.END_CHAR).end.endif): pass
    return ''.join(out)

def remove_empty_lines(s):
    p, out = Parser(s), []
    while p.is_active and (
          p.if_.x1_(p.chars('^\n$'), acc=out).endif.
          if_.x1('\n', out).x0_(p.sr(lambda p: p.x0_(In('\t ')).x1('\n'))).
          elif_.x1('\n').else_.x1(p.END_CHAR).end.endif): pass
    return ''.join(out)

def remove_trailing_ws(s):
    p, out = Parser(s), []
    while p.is_active and (
        p.if_.x0_(p.chars('^ $'), acc=out).endif.
          if_.x1(' ').x0_(' ').x1('\n', out).
          elif_.x1(' ', out).
          else_.x1(p.END_CHAR, out).end.
          endif): pass
    return ''.join(out)

def remove_debug(s):
    p, out = Parser(s), []

    @p.sr
    def body(p: Parser, indent):
        body_indent = indent.copy()
        return (p.x1(' ', acc=body_indent).x1_(p.chars('^\n$')).
                  x0_(p.sr(lambda p: p.x1('\n').at_least(len(body_indent), ' ').x1_(p.chars('^\n$')))))
    @p.sr
    def inline_body(p: Parser):
        return p.x1_(p.chars('^\n$'))
    @p.sr
    def if_dbg(p: Parser, out):
        indent = Val()
        else_body = []
        return (p.x1('\n').x0_(' ', acc=indent).x1('if').x1(' ').x1('__debug__').x0_(' ').x1(':').x0_(' ').
                  if_.x1(inline_body).
                  else_.x1('\n').x1(body, indent).
                  endif.
                  # ELSE branch: promoted to same indent as IF
                  if_.x1('\n').exactly(len(indent), ' ').x1('else').x0_(' ').x1(':').x0_(' ').
                      do(else_body.append, '\n').
                      if_.x1(inline_body, acc=else_body).
                      else_.x1('\n').x1(body, indent, acc=else_body).
                      endif.
                      do(out.append, indent_text( dedent(''.join(else_body)), indent.value )).
                  endif)

    while p.is_active and (
        p.if_.x1_(p.chars('^\n$'), acc=out).endif.
          if_.x1(if_dbg, out).
          elif_.x1('\n', acc=out).
          else_.x1(p.END_CHAR, acc=out).end.
          endif): pass
    return ''.join(out)



@pytest.mark.parametrize("src, expected_val",
[ ("x = 42  # This is a comment", "x = 42  "),
  ("x = 42  # This is a comment\n hello=3", "x = 42\n hello=3"),
("""\
def func():
    '''This is a docstring'''
    #and this another triple quote docstring''':
    \"""This is a docstring\"""
    x = 42  # comment
    if __debug__:
        print("Debug #mode")  # another comment
        if p.tracing:
            print(f"At {p.pos}: {p.ch!r}")
    # also a comment
    if __debug__:  print("Inline debug block")
    a = 3
    if __debug__:
        print("Another debug block")
    else:
        print("Not debug")
        if done:
            print("not debug: done")
    return x
    if __debug__:  print("last Inline debug block")
    else: print("last Inline non-debug block")
    #last comment
""",
"""\
def func():
    x = 42
    a = 3
    print("Not debug")
    if done:
        print("not debug: done")
    return x
    print("last Inline non-debug block")
"""),

])
def test_minify(src, expected_val):

    got = remove_comments(src)
    print(got)
    print(f"Got: {got!r}")
    got = remove_empty_lines(got)
    print(got)
    print(f"Got: {got!r}")
    got = remove_trailing_ws(got)
    print(got)
    print(f"Got: {got!r}")
    got = remove_debug(got)
    print(got)
    print(f"Got: {got!r}")
    print(f"Exp: {expected_val!r}")

    assert got == expected_val



TRAILING_SPACE_SET = [
    ("abc def  ]", "abc def", '  ]'),
    ("abc def]", "abc def", ']'),
    ("abc def  ghi   ]", "abc def  ghi", '   ]'),
    ("abc]", "abc", ']'),
    (" ]", "", ' ]'),
    ("]", "", ']'),
]

@pytest.mark.parametrize("src, expected_val, trailing", TRAILING_SPACE_SET)
def test_trailing_space(src, expected_val, trailing):
    p = Parser(src)

    ok = p.x1(name := p.sr(lambda p: (
        p.x0_(p.chars('^=\r\n#;[] \t$')).
        if_.x1_(In(' \t')).
            if_.one(']').back_ok.else_.one(name).endif.
        endif)), acc = (val :=Val())).is_ok
    print(p)
    print(f"Name: {val.value}")
    assert ok
    assert val.value == expected_val
    assert p.one(trailing).is_ok

@pytest.mark.parametrize("src, expected_val, trailing", TRAILING_SPACE_SET)
def test_trailing_space_with_back(src, expected_val, trailing):
    p = Parser(src)

    ok = p.x1(name := p.sr(lambda p: (
        p.x0_(p.chars('^=\r\n#;[] \t$')).
        if_.x0_(In(' \t')).one(']').back_ok.
        else_.x0_(In(' \t')).one(name).
        endif)), acc = (val :=Val())).is_ok
    print(p)
    print(f"Name: {val.value}")
    assert ok
    assert val.value == expected_val
    assert p.one(trailing).is_ok


@pytest.mark.parametrize("src, expected_val, trailing", TRAILING_SPACE_SET)
def test_trailing_space_with_peek(src, expected_val, trailing):
    p = Parser(src)

    ok = p.x1(name := p.sr(lambda p: (
        p.x0_(p.chars('^=\r\n#;[] \t$')).
        if_.peek(p.sr(lambda p: p.x0_(In(' \t')).one(']'))).
        else_.x0_(In(' \t')).one(name).
        endif)), acc = (val :=Val())).is_ok
    print(p)
    print(f"Name: {val.value}")
    assert ok
    assert val.value == expected_val
    assert p.one(trailing).is_ok



# ------------------ JSON parser  ------------------
# ebnf:
# value  = object | array | string | number | "true" | "false" | "null"
# object = "{" ws [ member ( ws "," ws member )* ] ws "}"
# member = string ws ":" ws value
# array  = "[" ws [ value ( ws "," ws value )* ] ws "]"
# string = '"' chars '"'
# number = '-'? int frac? exp?
# int    = '0' | [1-9] [0-9]*
# frac   = '.' [0-9]+
# exp    = ('e'|'E') ('+'|'-')? [0-9]+
# ws     = (space | tab | newline | carriage return)*
def parse_json(s: str):
    p = Parser(s)  # create parser instance with input string

    @p.subroutine # JSON value
    def j_val(p: Parser, out, **_kwargs):
        return (p.ws. # skip whitespace
                if_.one({'null': None, 'true': True, 'false': False}, out).
                elif_.one(p.decimal, out).
                elif_.one(p.string, out, quotes={'"':'"'}). # JSON strings are double-quoted only
                elif_.one(p.collection, j_val, l := []).do(p.accumulate, out, l). # array [...]
                else_.one(p.collection, j_kv, d := {}, brackets={'{': '}'}).do(p.accumulate, out, d). # object {...}
                endif)

    @p.subroutine # key:value pair in JSON object
    def j_kv(p: Parser, out, **_kwargs):
        return p.one(p.string, k := p.Val(), quotes={'"':'"'}).ws.one(':').ws.one(j_val, (out, k))

    r = Val() # resulting JSON goes here
    p.ws.one(j_val, r, nomatch='Invalid JSON').ws.one(p.END_CHAR, nomatch='Unexpected trailing input')
    return r.v


@pytest.mark.parametrize("json_source, result",
    [   (" null ", None),
        (" true ", True),
        (" false ", False),
        ("0", 0),
        ("-0", 0),
        ("42", 42),
        ("-13", -13),
        ("3.14", 3.14),
        ("-2.0", -2.0),
        ("6.02e23", 6.02e23),
        ("-1E-9", -1e-9),
        ('"hi\\n\\u20AC"', 'hi\n€'),
        (" 01 ", 1),  # permissive decimal: leading zero allowed by design

        (" [1, 2, 3] ", [1, 2, 3]),
        (' {"name":"Alice","age":30,"active":true,"misc":null} ',
           {"name": "Alice", "age": 30, "active": True, "misc": None}),
        ('{"a" : [ 1, {"b": [2,3] } ]}', {"a": [1, {"b": [2, 3]}]}),
    ],
)
def test_parse_json(json_source, result):
    assert parse_json(json_source) == result


def test_parse_json_errors():
    with pytest.raises(ValueError):
        parse_json(' [1,2, ')
    with pytest.raises(ValueError):
        parse_json(' {"a": 1, ')
    with pytest.raises(ValueError):
        parse_json(' {"a" 1} ')
    with pytest.raises(ValueError, match="Unexpected trailing input at:  {\"a\": 1} e̲xtra... "):
        parse_json(' {"a": 1} extra... ')


# ------------------ INI/Config parser  ------------------
# ini           = { ws* ( section | key_value | comment | empty_line ) } ;
# section       = ws* "[" ws* section_name ws* "]" ws* nl ;
# section_name  = 1*( char - "[" - "]" - nl ) ;
# key_value     = ws* key ws* "=" ws* value ws* comment? nl ;
# key           = { char - "=" - "[" - "]" - "#" - ";" - nl } ;
# value         = quoted_string | number | boolean | null | bare_value ;
# quoted_string = Parser.string ; (* supports both " " and ' ' quotes, with escapes *)
# number        = Parser.decimal ;  (* permissive: allows leading 0, exp, and fractions per Parser.decimal *)
# boolean       = "true" | "false" | "on" | "off" | "yes" | "no"  ;  (* case-insensitive *)
# null          = "null" | "none" ;  (* case-insensitive *)
# bare_value    = { char - "#" - ";" - nl } ;  (* then trimmed *)
# comment       = ws* ("#" | ";") { char - nl } nl ;
# empty_line    = ws* nl ;
# ws            = " " | "\t" ;
# nl            = "\r\n" | "\n" ;
# char          = ? any Unicode character ? ;

def parse_ini(s: str):
    p = Parser(s)  # new parser with input string
    cfg: dict[str, dict] = {}  # result goes here
    current_sec = Val(None)    # current section name or None (DEFAULT)

    def _enter_section(name: str):  # emitter: [section]
        current_sec.set(name)
        cfg.setdefault(name, {})

    def _set_kv(k: str, v):   # emitter: key = value
        sec = current_sec.value or 'DEFAULT'
        cfg.setdefault(sec, {})
        cfg[sec][k] = v

    ws = In(' \t')     # whitespace matcher
    nl = ('\r\n','\n') # newline matcher

    @p.subroutine # a comment or empty line(s)
    def comment_or_empty(p: Parser):
        return (p.zero_or_more(ws). # optional leading spaces
                if_.one(('#', ';')).x0_(p.chars('^\n\r$')).zero_or_more(nl).
                elif_.one_or_more(nl). # empty line(s) ?
                else_.one(p.END_CHAR).end.endif) # if not end-of-input return False

    @p.subroutine # value of a key=value pair
    def value(p: Parser, out):
        return (p.if_.one(p.string, out).  # support both " " and ' '
                elif_.one(p.decimal, out). # number
                elif_.one({'true' : True, 'false': False, # bool literals
                           'on'  : True, 'off'  : False,
                           'yes' : True, 'no'   : False,  # ic -> ignore case
                           'null': None, 'none' : None}, out, ic=True).
                # bare value until comment/EOL:
                else_.one_or_more(p.chars('^#;\n\r$'), acc=lambda v: p.accumulate(out, v.strip())).
                endif)

    # Lets use aliases, x1 (one), x1_ (one_or_more), x0_ (zero_or_more), etc., for shorter lines:

    @p.subroutine # [section] header
    def section(p: Parser):
        name = Val('')
        return (p.x0_(ws).x1('[').
                x0_(ws).x1_(p.chars('^[]\n\r$'), acc=(name, lambda _: name.rstrip()), nomatch="Empty section name").
                x1(']', nomatch="Expected ']' after section name").x0_(ws).
                x1(nl, nomatch="Expected newline after section header").
                err_if(Not(name), "Empty section name").
                do(_enter_section, name.value))

    @p.subroutine # key = value
    def key_value(p: Parser):
        key = Val('')
        return (p.x0_(ws).
                x1_(p.chars('^;#=[]\n\r$'), acc=(key, lambda _: key.rstrip())).
                do_if(key, lambda: (p.
                    x1('=', nomatch="Expected '='").err_if(Not(key), "Empty key name").x0_(ws).
                    if_.x1(value, val := Val()).
                        x0_(ws).x0_(p.chars('^\n\r$')).x0_(nl).
                        do(_set_kv, key.value, val.value).
                    else_.err("Invalid key-value pair").endif)))

    while p.is_active and (p.   # main loop:
        x0_(comment_or_empty).  # - skip any comments/empty lines
        x0_1(section).          # - optional section header
        x0_1(key_value)): pass  # - optional key=value pairs

    return cfg

def print_ini(cfg: dict):
    # print config, with newline after each item, with indented sections
    for sec, items in cfg.items():
        print(f"[{sec}]")
        for k, v in items.items():
            print(f"  {k} = {v!r}")


@pytest.mark.parametrize("src, expected_cfg", [
    ("""
; top comment
[ core ]
user = alice


count = 3
pi = 3.14

active = true
path = "/tmp/data"  # inline ok

# another
[server]
host=localhost ; comments
port=8080
""",
     {
        'core': {
            'user': 'alice',
            'count': 3,
            'pi': 3.14,
            'active': True,
            'path': '/tmp/data',
        },
        'server': {
            'host': 'localhost',
            'port': 8080,
        },
     }),
    ("a = 1\nb = two\n",
     {'DEFAULT': {'a': 1, 'b': 'two'}}),
    ("key = value without newline", {'DEFAULT': {'key': 'value without newline'}}),
    ("key = value with another = inside\r\n", {'DEFAULT': {'key': 'value with another = inside'}}),

])
def test_parse_ini(src, expected_cfg):
    Parser.PARSE_LIMIT = 40
    cfg = parse_ini(dedent(src))
    # print config, with newline after each item, with indented sections
    print_ini(cfg)
    print("GOT:", cfg)
    print("EXP:", expected_cfg)

    assert cfg == expected_cfg

@pytest.mark.parametrize("src, err_type, err_str", [
    ("[bad\n", ValueError, "Expected ']' after section name at: [bad"),
    ("just text\n", ValueError, "Expected '=' at: just text"),
    ("key\n", ValueError, "Expected '=' at: key"),
    ("[ ]\nkey = value\n", ValueError, "Empty section name"),
    ("[ ] key = value\n", ValueError, "Empty section name at"),
    ("[section] key = value\n", ValueError, "Expected newline after section header"),
    ("[section\nkey = value\n", ValueError, "Expected ']' after section name at: [section"),
    ("[section]\nkey = value\n[bad\n", ValueError, "Expected ']' after section name at: …value\n[bad"),
])
def test_parse_ini_errors(src, err_type, err_str):
    with pytest.raises(err_type, match=re.escape(err_str)):
        cfg = parse_ini(src)
        print_ini(cfg)
        print("GOT:", cfg)


# ------------------ CSV parser  ------------------
# csv           = record , { nl , record } , [ nl ] ;
# record        = field , { "," , field } ;
# field         = quoted_field | bare_field ;
# quoted_field  = '"' , { qchar | '""' } , '"' ;
# bare_field    = { char - '"' - "," - nl } ;
# qchar         = char - '"' ;
# char          = ? any Unicode character except newline ? ;
# nl            = "\r\n" | "\n" ;
def parse_csv(s: str):
    p = Parser(s)
    rows = []

    nl = ('\r\n', '\n') # newline matcher

    @p.subroutine # quoted field: '"' { qchar | '""' } '"'
    def quoted_field(p: Parser, out):

        @p.subroutine # Escaped doubled quote "" (=> ") stop on first unescaped non-quote char
        def qcontent(p: Parser, out):
            return p.if_.one('""').do(out.append, '"').else_.x1_(p.chars('^"$'), acc=out).endif

        return p.one('"').x0_(qcontent, txt := Val('')).one('"').do(out.append, txt.value)

    @p.subroutine # Any chars except quote, comma, or newline
    def bare_field(p: Parser, out):
        txt = Val()
        return p.x0_(p.chars('^",\r\n$'), acc=txt).do(out.append, txt.value)

    @p.subroutine # field = quoted_field | bare_field
    def field(p: Parser, out):
        return p.if_.one(quoted_field, out).else_.one(bare_field, out).endif

    @p.subroutine # record = field { "," field }
    def record(p: Parser):
        row = []
        return (p.one(field, row).
                  x0_(p.sr(lambda p: p.one(',').one(field, row))).
                  do_if(lambda: not (len(row) == 1 and row[0] is None), rows.append, row))

    # csv = record { nl record } [ nl ] EOF
    p.one(record, nomatch='Invalid CSV record') \
     .x0_(p.sr(lambda p: p.one(nl).one(record))) \
     .x0_(nl) \
     .one(p.END_CHAR, nomatch='Unexpected trailing input')

    return rows


@pytest.mark.parametrize("src, rows", [
    ("a,b,c", [["a", "b", "c"]]),
    ('a,"b",c', [["a", "b", "c"]]),
    ('"a,b",c', [["a,b", "c"]]),
    ('"a""b",c', [['a"b', "c"]]),
    ("a,,c", [["a", None, "c"]]),
    (",a,b,", [[None, "a", "b", None]]),
    ('"a\nb",c', [["a\nb", "c"]]),  # newline in quoted field
    ('""', [['']]), # empty quoted field
    ("a,b\r\nc,d\r\ne,f\n", [["a", "b"], ["c", "d"], ["e", "f"]]),
    ("a,b\r\n\r\nc,d\r\ne,f\n", [["a", "b"], ["c", "d"], ["e", "f"]]),
    ("a,b,\n,\n", [["a", "b", None], [None, None]]),
])
def test_parse_csv_ok(src, rows):
    got = parse_csv(src)
    print("\n".join(str(r) for r in got))
    assert got == rows


@pytest.mark.parametrize("src", [
    'a,"b',           # unterminated quoted field
    '"a\nb,c',        # unterminated quoted field with newline
    'a,b\n"c,d',      # unterminated quote on second row
])
def test_parse_csv_errors(src):
    with pytest.raises(ValueError):
        parse_csv(src)



def parse_char_spec(spec: str):
    """Parse a regex-like char class spec (without surrounding []). `'^a-z#%1-9$'`

    Supported:
        - Leading '^' negates the class.
        - Trailing '$' adds END_CHAR to the class.
        - Ranges 'a-z' (inclusive). If reversed (z-a), we expand the shorter→longer anyway.
        - Escapes: \\\\\\\\, \\\\-, \\\\^, \\\\$.
        - Literal '-' if first/last, between two ranges, or escaped.

    Returns:
        (chars_str, negate_bool, include_end_bool)
    """
    p = Parser(spec)
    trailing_eof = Val(False) # set to True if $ is present at end
    @p.sr # escaped or plain char, esc flag will be True if escaped
    def char(p, out, esc = None):
        return p.if_.one('\\').one(p.NOT_END_CHAR, out, esc).else_.one(p.NOT_END_CHAR, out).endif
    @p.sr # range: 'a-z' → ('a','z') appended to out
    def range_(p, left, out):
        return p.one('-').one(char, e := Val()).do(lambda: out.append((left, e.v)))
    @p.sr # range, char, or trailing '$'
    def atom(p, out):
        return (p.one(char, left := Val(), esc := Val(False)).
                if_.one(range_, left.v, out).
                elif_.fail_if(esc or left != '$').one(p.END_CHAR, lambda _: trailing_eof.set(True)).
                else_.do(out.append, left.v).endif)

    p.zero_or_one('^', neg := Val(False)).zero_or_more(atom, r := [])
    return r, neg.v, trailing_eof.v # -> [('a','z'), 'A'], True, False


def parse_char_spec_alt(spec: str):
    """ Alt implementation of parse_char_spec using only one lookahead branch in atom()
    """
    p = Parser(spec)
    trailing_eof = Val(False) # set to True if $ is present at end
    @p.sr # escaped or plain char, esc flag will be True if escaped
    def char(p, out, esc = None):
        return p.if_.one('\\').one(p.NOT_END_CHAR, out, esc).else_.one(p.NOT_END_CHAR, out).endif
    @p.sr # range: 'a-z' → ('a','z') appended to out
    def range_(p, left, out):
        return p.one('-').one(char, e := Val()).do(lambda: out.append((left, e.v)))
    @p.sr # range, char, or trailing '$'
    def atom(p, out):
        return (p.one(char, left := Val(), esc := Val(False)).
                if_.one(range_, left.v, out).
                else_.do(lambda: trailing_eof.set(True) if (p.ch == p.END_CHAR and left == '$' and not esc)
                                 else out.append(left.v)).endif)

    p.zero_or_one('^', neg := Val(False)).zero_or_more(atom, r := [])
    return r, neg.v, trailing_eof.v # -> [('a','z'), 'A'], True, False


CHAR_SPEC_SET = [
    ('a',               ['a'], False, False),
    ('',                [],    False, False),
    ('^',               [],    True,  False),
    ('$',               [],    False, True),
    ('^$',              [],    True,  True),
    ('\\^',             ['^'], False,  False),
    ('^a',              ['a'], True,  False),
    ('\\^a',            ['^', 'a'], False,  False),
    ('abc',             ['a', 'b', 'c'], False, False),
    ('^abc',            ['a', 'b', 'c'], True,  False),
    ('^abc$',           ['a', 'b', 'c'], True,  True),
    ('^abc$d',          ['a', 'b', 'c', '$', 'd'], True,  False),
    ('^a-zA$',          [('a', 'z'), 'A'], True,  True),
    ('a-zA$',           [('a', 'z'), 'A'], False,  True),
    ('a-zA\\$',         [('a', 'z'), 'A', '$'], False,  False),
    ('a-zA',            [('a', 'z'), 'A'], False,  False),
    ('a-z',             [('a', 'z')], False,  False),
    ('--z',             [('-', 'z')], False,  False),
    ('a-',              ['a', '-'], False,  False),
    ('-a',              ['-', 'a'], False,  False),
    ('a-z1-9',          [('a', 'z'), ('1', '9')], False,  False),
    ('a-z-1-9',         [('a', 'z'), '-', ('1', '9')], False,  False),
    ('a-z-9',           [('a', 'z'), '-', '9'], False,  False),
    ('a\\-z-9',         ['a', '-', ('z', '9')], False,  False),
]

@pytest.mark.parametrize("spec, expected, neg, eof", CHAR_SPEC_SET)
def test_parse_chars(spec, expected, neg, eof):
    got, got_neg, got_eof = parse_char_spec(spec)
    print('IN: ', spec)
    print('GOT:', got, got_neg, got_eof)
    print('EXP:', expected, neg, eof)
    assert got == expected
    assert got_neg == neg
    assert got_eof == eof

@pytest.mark.parametrize("spec, expected, neg, eof", CHAR_SPEC_SET)
def test_parse_chars_alt(spec, expected, neg, eof):
    got, got_neg, got_eof = parse_char_spec_alt(spec)
    print('IN: ', spec)
    print('GOT:', got, got_neg, got_eof)
    print('EXP:', expected, neg, eof)
    assert got == expected
    assert got_neg == neg
    assert got_eof == eof
