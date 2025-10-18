# Development

## Prerequisites
- Python 3.10+
- flit (for build/publish). Install with:
```sh
python -m pip install -U flit
# or: pipx install flit
```


## Pulling the project
```sh
git clone https://github.com/anptrs/parsek.git
cd parsek
```


## Editable install (project root)
First install with editable option (run from project's root, parsek dir)
```sh
$ flit install --symlink
```
This lets you edit the module without reinstalling and enables tests to import the local package.
Alternatively, without flit:
```sh
python -m pip install -e .
```


## Testing
Run tests from project's root:
```sh
# Optimized mode (removes asserts and tracing via __debug__ == False)
$ python -O -m pytest

# Regular mode with tracing enabled (slower)
$ python -m pytest --parser-trace 5

```
- The `-O` flag removes all `assert` statements and all tracing support in the module.
- `--parser-trace` sets the tracing level: 0-5 (default 3); 0 - disables all tracing (optimized away even if not `-O`), 5 - most verbose. `--parser-trace` only has effect without `-O`.
- Trace output is shown only on test failures. Tracing slows down parsing significantly. That's why the tests run as long as they do as tracing enabled (level 3) by default.
- **Important**: make sure to test both with and without `-O` to cover all code paths.


## Coverage testing
The included tests achieve 100% code coverage in `parsek.py`. To get a coverage (with branches) report, execute the following in the terminal:
```sh
$ python -m coverage run --branch -m pytest
$ python -m coverage html
```
This will run the tests and generate HTML coverage report. Open `htmlcov/index.html` in a web browser to verify that all statements/branches in `src/parsek.py` are covered.


## Building and testing the minified version
To make the minified version (in project's root):
```sh
$ python utils/minify.py src/parsek.py
```
This will create `parsek_min.py` in the project's root.
Then run the tests with the `--use-parsek-min` option:
```sh
$ python -m pytest --use-parsek-min
```


## Release (maintainers)
```sh
# Build
flit build
# Publish to PyPI
flit publish
```


## Project Goals
- **Small**: single-file, pure-Python, zero-dependencies. The module is designed to be a simple drop-in solution for projects that need parsing capabilities without the overhead of large dependencies. A minified build is provided via `utils/minify.py` for single-file plugin environments.
- **Fast**: efficient parsing core.
- **Expressive**: functional combinator style for expressive and readable grammar definitions.
- **Debuggable**: built-in tracing and debugging support to help diagnose parsing issues.


## Project Status
- Fully functional and stable.
- Tests provide 100% statement and branch coverage in `src/parsek.py`.
