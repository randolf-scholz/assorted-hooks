# custom pre-commit hooks

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## python-based hooks (using AST — will not import your code)

## `check-imported-attributes`

This hook checks that if both a module is imported and some class/function from that module, always the directly imported symbol is used.

```python
import collections.abc as abc
from collections.abc import Sequence

def foo(x: Sequence) -> Sequence:
    assert isinstance(x, abc.Sequence)  # <- use Sequence instead of abc.Sequence
    return x
```

## `prefer-abc-typing`

Checks that `collections.abc` is used instead of `typing` for Protocols (`Sequence`, `Mapping`, etc.).

## `python-no-mixed-args`

Checks that all function definitions allow no `POSITIONAL_OR_KEYWORD` arguments. Only `POSITIONAL_ONLY`, `KEYWORD_ONLY`, `VAR_POSITIONAL` and `VAR_KEYWORD` are allowed.

Options:

- `--allow-one` allows a single `POSITIONAL_OR_KEYWORD` argument
  This is often ok, since there is no ambiguity of the order of arguments.
- `--ignore-overloads`: skip function defs that are overloads of other function defs. (default: `True`)
- `--ignore-names`: skip function defs with specific names (default: `[]`)
- `--ignore-decorators`: skip function defs with specific decorators (default: `[]`)
- `--ignore-dunder`: skip function defs that are dunder methods (default: `False`)
- `--ignore-private`: skip function defs that are private (default: `False`)
- `--ignore-without-positional-only`: skip function defs that don't have any `POSITIONAL_ONLY` arguments. (default: `False`)

Excluded are:

- Lambdas
- functions inside docstrings
- functions of the form `def foo(self): ...` (self is excluded)
- functions of the form `def foo(cls): ...` (cls is excluded)

### `check-__all__-exists`

- Checks that `__all__` is defined in all modules.
- Checks that `__all__` is defined at the top of the file.
  - `__all__` should only be preceded by the module docstring and `__future__` imports.
- Checks that `__all__` is defined as a literal list (not tuple, set, etc.)
- Checks that `__all__` is not defined multiple times.
- Checks that `__all__` is not superfluous (i.e. contains all symbols defined in the module)

### `check-clean-interface`

- Checks that `dir(module)` is equal to `__all__` (i.e. that `__all__` contains all symbols defined in the module).
- By default only applies to packages (i.e.`__init__.py` files).
- Generally if something is not in `__all__` it should not be used outside the module, functions, classes and constants
  that are not exported should be given a name with a single leading underscore: `_private`

### `check-typing`

AST based linting rules for python type hints. By default, all checks are disabled.

- `--check-no-return-union`: checks that `Union` is not used as a return type. One may want to disallow `Union` as a return type because it makes functions harder to use, as callers have to check the type of the return value before using it.
  NOTE: `Optional` is intentionally excluded from this rule, as it is a common pattern to use.
- `--check-pep604-union`: checks that [PEP604](https://www.python.org/dev/peps/pep-0604/) style unions (`X | Y`) are used instead of old style unions (`Union[X, Y]`).
- `--check-no-optional`: checks that `None | X` is used instead of `Optional[X]`.
- `--check-optional`: checks that `Optional[X]` is used instead of `None | X`.
- `--check-overload-default-ellipsis`: checks that inside `@overload` default values are set to `...`.
- `--check-no-future-annotations`: checks that `from __future__ import annotations` is not used.
- `--check-no-hints-overload-implementation`: checks that the implementation of an overloaded function does not have type hints.
- `--check-no-tuple-isinstance`: checks that unions are used instead of tuples in isinstance.
- `--check-no-union-isinstance`: checks that tuples are used instead of unions in isinstance.

### `check_naming_convention` (not implemented yet)

Checks that naming conventions are followed. Defaults:

- constants: exported: `UPPERCASE_WITH_UNDERSCORES`, internal: `_UPPERCASE_WITH_UNDERSCORES`, special: `__dunder__`
- functions: exported: `snake_case`, internal: `_snake_case`, special: `__dunder__`
- classes: exported: `PascalCase`, internal: `_PascalCase`, special: `__dunder__`

## Script-based hooks (may import your code)

### `pyproject-validate-version`

Verifies that the version in `pyproject.toml` adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/).

Details: https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions

### `pyproject-update-deps`

**NOTE: THIS HOOK IS SET TO MANUAL BY DEFAULT. RUN VIA**

```bash
pre-commit run --hook-stage manual pyproject-update-deps
```

Updates dependencies in `pyproject.toml`.

- `"package>=version"` ⟶ `"package>=currently_installed"` (`[project]` section)
- `package=">=version"` ⟶ `package=">=currently_installed"` (`[tool.poetry]` section)
- `package={version=">=version"` ⟶ `package={version=">=currently_installed"` (`[tool.poetry]` section)

### `pyproject-check-dependencies`

Analyzes all `import`-statements and makes sure all third-party dependencies are listed in `pyproject.toml`. Can be
applied to test-dependencies as well. This catches missing implicit dependencies, for example package `panads`
depends on `numpy` but numpy should still be listed in `pyproject.toml` if it is used explicitly.

## pygrep-based hooks

### `python-no-blanket-type-ignore`

A modified version of the hook at https://github.com/pre-commit/pygrep-hooks.

- allows `# type: ignore` at the top of the file to ignore the whole file (cf. https://github.com/python/mypy/issues/964)
- colon after "type" non-optional.

### `python-no-builtin-eval`

A modified version of the hook at https://github.com/pre-commit/pygrep-hooks.

- allows `<obj>.eval`, e.g. `pandas.eval`.
- only blank `eval(` and `builtins.eval(` are forbidden.

### `check-separator-length`

Tests that "line-break" comments a la

```python
# ------------------------------------------------------
```

are exactly 88 characters long.

### `python-consider-using-raw-string`

Hints that triple quoted strings should be raw strings (convention).
Ignores triple quoted f-strings.
