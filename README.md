# custom pre-commit hooks

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## `check-imported-attributes`

This hook checks that if both a module is imported and some class/function from that module, always the directly imported symbol is used.

```python
import collections.abc as abc
from collections.abc import Sequence

def foo(x: Sequence) -> Sequence:
    assert isinstance(x, abc.Sequence)  # <- use Sequence instead of abc.Sequence
    return x
```

## `jupyter-clear-output`

This hook clears the output of jupyter notebooks. This is useful to avoid large diffs in commits. Use the `files`
and `exclude` configuration options to specify which notebooks should be spared.

## `pyproject-validate-version`

Verifies that the version in `pyproject.toml` adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/).

Details: https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions

## `pyproject-update-deps`

Updates dependencies in `pyproject.toml`.

- `"package>=version"` ⟶ `"package>=currently_installed"` (`[project]` section)
- `package=">=version"` ⟶ `package=">=currently_installed"` (`[tool.poetry]` section)
- `package={version=">=version"` ⟶ `package={version=">=currently_installed"` (`[tool.poetry]` section)

## `pyproject-check-dependencies`

Analyzes all `import`-statements and makes sure all third-party dependencies are listed in `pyproject.toml`. Can be
applied to test-dependencies as well. This catches missing implicit dependencies, for example package `panads`
depends on `numpy` but numpy should still be listed in `pyproject.toml` if it is used explicitly.

## `no-mixed-args`

Checks that all function definitions allow no `POSITIONAL_OR_KEYWORD` arguments. Only `POSITIONAL_ONLY`, `KEYWORD_ONLY`, `VAR_POSITIONAL` and `VAR_KEYWORD` are allowed.

Options:

- `--allow-one` allows a single `POSITIONAL_OR_KEYWORD` argument
  This is often ok, since there is no ambiguity of the order of arguments.
- `--skip-non-po`: skip function defs that don't have any `POSITIONAL_ONLY` arguments.
- `--ignore-overloads`: skip function defs that are overloads of other function defs. (default: `True`)

Excluded are:

- Lambdas
- functions inside docstrings
- functions of the form `def foo(self): ...` (self is excluded)
- functions of the form `def foo(cls): ...` (cls is excluded)

## `python-no-blanket-type-ignore`

A modified version of the hook at https://github.com/pre-commit/pygrep-hooks.

- allows `# type: ignore` at the top of the file to ignore the whole file (cf. https://github.com/python/mypy/issues/964)
- colon after "type" non-optional.

## `python-no-builtin-eval`

A modified version of the hook at https://github.com/pre-commit/pygrep-hooks.

- allows `<obj>.eval`, e.g. `pandas.eval`.
- only blank `eval(` and `builtins.eval(` are forbidden.
