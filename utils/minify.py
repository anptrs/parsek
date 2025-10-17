""" Utility script to minify python source code by removing comments, docstrings, empty lines,
    trailing whitespace, assertions and blocks of code under `if __debug__:`.

    Note, this script is specifically designed for `parsek.py` as input. It will
    __certainly__ fail processing other source code.

    Usage: `python utils.minify input.py -o output.py`
"""
import argparse
import sys

from pathlib import Path
from textwrap import dedent, indent as indent_text
from parsek import Parser, Val, In, Not, Raw

def remove_comments_and_triple_quotes(s):
    """ removes comments and ALL triple quoted strings from python source code """
    p, out = Parser(s), []
    # IMPORTANT NOTE:
    # removes all triple quote strings (not just docstrings), both '''...''' and """..."""
    # this DOES NOT handle escapes in triple quote strings so \``` will break it !!!
    @p.sr
    def triple_str(p: Parser):
        return p.one(('"""', "'''"), q := Val()).zero_or_more(Not(q)).one(q)

    while p.is_active and (
        p.x0_(p.chars('^\'"#rR$'), acc=out).
        if_.x1('#').x0_(p.chars('^\n$')).one('\n', out).
        elif_.x1(triple_str).
        elif_.x1(In('rR'), out).x1(p.string, escapes=Raw(), acc=out).
        elif_.x1(In('rR')). # rR is copied to out above even if string fails
        elif_.x1(p.string, acc=out).
        else_.x1(p.END_CHAR).end.endif): pass
    return ''.join(out)

def remove_empty_lines(s):
    """ removes empty lines from python source code """
    p, out = Parser(s), []
    while p.is_active and (
          p.if_.x1_(p.chars('^\n$'), acc=out).endif.
          if_.x1('\n', out).x0_(p.sr(lambda p: p.x0_(In('\t ')).x1('\n'))).
          elif_.x1('\n').else_.x1(p.END_CHAR).end.endif): pass
    return ''.join(out)

def remove_trailing_ws(s):
    """ removes trailing whitespace from each line of python source code """
    p, out = Parser(s), []
    while p.is_active and (
        p.if_.x0_(p.chars('^ $'), acc=out).endif.
          if_.x1(' ').x0_(' ').x1('\n', out).
          elif_.x1(' ', out).
          else_.x1(p.END_CHAR, out).end.
          endif): pass
    return ''.join(out)


def remove_debug(s):
    """ removes blocks of code under `if __debug__:` from python source code.
        Promotes `else:` blocks to the same indentation level as the corresponding `if __debug__:`
    """
    p, out = Parser(s), []
    count = Val(0)
    else_count = Val(0)

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
                  do(count.inc).
                  # ELSE branch: promoted to same indent as IF
                  if_.x1('\n').exactly(len(indent), ' ').x1('else').x0_(' ').x1(':').x0_(' ').
                      do(else_body.append, '\n').
                      if_.x1(inline_body, acc=else_body).
                      else_.x1('\n').x1(body, indent, acc=else_body).
                      endif.
                      do(else_count.inc).
                      do(out.append, indent_text( dedent(''.join(else_body)), indent.value )).
                  endif)

    while p.is_active and (
        p.if_.x1_(p.chars('^\n$'), acc=out).endif.
          if_.x1(if_dbg, out).
          elif_.x1('\n', acc=out).
          else_.x1(p.END_CHAR, acc=out).end.
          endif): pass
    if count:
        print(f"Removed {count.v} `if __debug__:` block(s)")
    if else_count:
        print(f"Promoted {else_count.v} `else:` not __debug__ block(s)")
    return ''.join(out)

def remove_assertions(s):
    """ removes assert statements from python source code
        IMPORTANT asserts have to be on a single line!!!
    """
    p, out = Parser(s), []
    count = Val(0)
    while p.is_active and (
          p.if_.x1_(p.chars('^\n$'), acc=out).endif.
          if_.x1('\n').x0_(' ').x1('assert ').x1_(p.chars('^\n$')).do(count.inc).
          elif_.x1('\n', out).else_.x1(p.END_CHAR).end.endif): pass
    if count:
        print(f"Removed {count.v} assert statement(s)")
    return ''.join(out)

def get_first_comment(s):
    """ returns the first comment in the python source code, or empty string if none found """
    p, out = Parser(s), []

    @p.subroutine
    def comment_line(p: Parser):
        return p.x1('#').x0_(p.chars('^\n$')).x1('\n')

    p.zero_or_more(comment_line, acc=out)
    return ''.join(out)



# Resolve parsek version from installed package metadata
try:
    from importlib.metadata import version as pkg_version
except Exception: # pylint: disable=broad-except
    try:
        from importlib_metadata import version as pkg_version
    except Exception: # pylint: disable=broad-except
        pkg_version = None # pylint: disable=invalid-name

def _find_pyproject(start_dir: Path) -> Path | None:
    cur = start_dir.resolve()
    root = cur.anchor
    while True:
        cand = cur / "pyproject.toml"
        if cand.is_file():
            return cand
        if str(cur) == root:
            return None
        cur = cur.parent

def _read_version_from_pyproject(start_dir) -> str | None:
    pyproject_path = _find_pyproject(start_dir)
    print("Reading pyproject.toml for version:", pyproject_path)
    try:
        with pyproject_path.open("rb") as f:
            data = f.read().decode("utf-8")
        in_project = False
        for l in data.splitlines():
            line = l.strip()
            if in_project:
                if line.startswith("version"):
                    _, _, ver = line.partition("=")
                    return ver.strip().strip('"').strip("'")
            elif line == "[project]":
                in_project = True
    except Exception:  # pylint: disable=broad-except
        return None
    return None

def _get_parsek_version(start_dir) -> str:
    if ver := _read_version_from_pyproject(start_dir):
        return ver
    print("WARNING: Could not read version from pyproject.toml, trying package metadata...")
    if pkg_version is None:
        return None
    try:
        return pkg_version("parsek")
    except Exception: # pylint: disable=broad-except
        return None


def minify(src, start_dir):
    """ minifies python source code by removing comments, docstrings, empty lines,
        trailing whitespace, asserts and blocks of code under `if __debug__:`.
    """
    print("Parsek version:", ver := _get_parsek_version(start_dir))
    first_comment = get_first_comment(src)
    out = remove_comments_and_triple_quotes(src)
    out = remove_empty_lines(out) # has to be before remove_debug() or it stops on empty lines
    out = remove_trailing_ws(out)
    out = remove_debug(out)
    out = remove_assertions(out)
    out = remove_empty_lines(out)
    out = remove_trailing_ws(out)

    if ver:
        first_comment = first_comment + f"# Parsek v{ver}\n"
    out = first_comment.rstrip() + out
    return out



# ---------------- CLI Support ----------------

def _derive_output_path(input_path: Path) -> Path:
    stem = input_path.stem
    suffix = input_path.suffix
    if not suffix:
        return input_path.with_name(f"{stem}_min")
    if suffix == ".py":
        return input_path.with_name(f"{stem}_min.py")
    return input_path.with_name(f"{input_path.name}_min")

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m parsek.utils.minify",
        description="Minify a Python source file (remove comments, docstrings, blank lines, trailing whitespace, debug blocks)."
    )
    parser.add_argument("input", help="Input Python source file (or - for stdin)")
    parser.add_argument("-o", "--output", help="Output filename (optional). If omitted, creates <name>_min.py in CWD.")
    parser.add_argument("-r", "--readonly", action="store_true",
                        help="Make the output file read-only (chmod 444).")

    args = parser.parse_args(argv)

    # Read source
    start_dir = None
    if args.input == "-":
        src_text = sys.stdin.read()
        input_path = Path("stdin.py")
        start_dir = Path.cwd()
    else:
        input_path = Path(args.input)
        if not input_path.is_file():
            parser.error(f"Input file not found: {input_path}")
        src_text = input_path.read_text(encoding="utf-8")
        start_dir = input_path.parent

    # Minify
    try:
        result = minify(src_text, start_dir)
    except Exception as e: # pylint: disable=broad-except
        print(f"Error during minification: {e}", file=sys.stderr)
        return 1

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path.cwd() / _derive_output_path(input_path).name
        if out_path.exists() and args.input != "-":
            print(f"Overwriting existing file: {out_path}", file=sys.stderr)

    # Write
    try:
        out_path.write_text(result, encoding="utf-8")
        try:
            if args.readonly:
                # Set POSIX read-only (owner/group/others)
                out_path.chmod(0o444)
        except Exception as e: # pylint: disable=broad-except
            print(f"Warning: Failed to set read-only mode on output file: {e}", file=sys.stderr)

    except Exception as e: # pylint: disable=broad-except
        print(f"Failed to write output file: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
