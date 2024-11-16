# check-requirements-maintained

This hook checks for dependencies that appear to be unmaintained,
by checking when the last release was published on PyPI.
This lookup is slow without using asynchronous requests powered by `aiohttp`.
Therefore, there are two versions of the hook:

## Additional Arguments

- `pyproject-check-unmaintained`: runs in a separate virtual environment, with `aiohttp` installed.
    This is much faster, but can only checks packages declared in `pyproject.toml`.
- `pyproject-check-unmaintained-local`: runs in the local virtual environment,
    and inspects all installed packages via `importlib.metadata.distributions`.
    If `aiohttp` is not installed, this hooks will be slow as it performs synchronous requests.
- `--threshold`: sets the threshold in days (default: 1000 ≈ 3 years)
