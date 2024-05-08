# custom pre-commit hooks

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

[ast-based hooks](#ast-based-hooks) | [script-based hooks](#script-based-hooks) | [pygrep-based hooks](#pygrep-based-hooks) | [latex hooks](#latex-hooks) | [changelog](CHANGELOG.md)

## AST-based Hooks

### `python-direct-imports`

This hook checks that if both a module is imported and some class/function from that module, always the directly imported symbol is used:

```python
import collections
from collections import defaultdict  # <- directly imported

d = collections.defaultdict(int)  # <- use defaultdict directly!
```

### `python-standard-generics`

Checks that `collections.abc` is used instead of `typing`/`typing_extensions` whenever possible,
for example for `Sequence`, `Mapping`, etc.

### `python-no-mixed-args`

Checks that all function definitions allow no `POSITIONAL_OR_KEYWORD` arguments.
Only `POSITIONAL_ONLY`, `KEYWORD_ONLY`, `VAR_POSITIONAL` and `VAR_KEYWORD` are allowed.
Excludes are lambda functions, functions inside docstrings, and the arguments `self` and `cls`.
Options:

- `--allow-one` allows a single `POSITIONAL_OR_KEYWORD` argument. This is often ok, since there is no ambiguity of the order of arguments. (default: `False`)
- `--allow-two` allows two `POSITIONAL_OR_KEYWORD` arguments. (default: `False`)
- `--ignore-dunder`: skip function defs that are dunder methods (default: `False`)
- `--ignore-private`: skip function defs that are private (default: `False`)
- `--ignore-overloads`: skip function defs that are overloads of other function defs. (default: `True`)
- `--ignore-without-positional-only`: skip function defs that don't have any `POSITIONAL_ONLY` arguments. (default: `False`)
- `--ignore-names *names`: skip function defs with specific names (default: `[]`)
- `--ignore-decorators *names`: skip function defs with specific decorators (default: `[]`)

### `python-dunder-all`

- Checks that `__all__` is defined in all modules.
- Checks that `__all__` is defined at the top of the file.
  - `__all__` should only be preceded by the module docstring and `__future__` imports.
- Checks that `__all__` is defined as a literal list (not tuple, set, etc.)
- Checks that `__all__` is not defined multiple times.
- Checks that `__all__` is not superfluous (i.e. contains all symbols defined in the module)

### `python-check-typing`

AST based linting rules for python type hints. Default settings are

- [x] `--check-typealias-union`: Checks that `UnionType` is used instead `TypeAlias` when appropriate.
- [x] `--check-pep604-union`: checks that [PEP604](https://www.python.org/dev/peps/pep-0604/) style unions (`X | Y`) are used instead of old style unions (`Union[X, Y]`).
- [x] `--check-no-future-annotations`: checks that `from __future__ import annotations` is not used.
- [x] `--check-overload-default-ellipsis`: checks that inside `@overload` default values are set to `...`.
- [ ] `--check-no-optional`: checks that `None | X` is used instead of `Optional[X]`.
- [ ] `--check-optional`: checks that `Optional[X]` is used instead of `None | X`.
- [ ] `--check-no-hints-overload-implementation`: checks that the implementation of an overloaded function does not have type hints.
- [ ] `--check-no-tuple-isinstance`: checks that unions are used instead of tuples in isinstance.
- [ ] `--check-no-union-isinstance`: checks that tuples are used instead of unions in isinstance.
- [ ] `--check-no-return-union`: checks that `Union` is not used as a return type.
      One may want to disallow `Union` as a return type because it makes functions harder to use,
      as callers have to check the type of the return value before using it.
  NOTE: `Optional` is intentionally excluded from this rule, as it is a common pattern to use.
- [ ] `--check-no-return-union-recursive`: Same as `--check-no-return-union`, but checks for `Union` recursively (e.g. disallows `list[int | str]`.

## Script-based hooks

⚠️ These hooks may import your code. ⚠️

### `python-clean-interface`

- Checks that `dir(module)` is equal to `__all__` (i.e. that `__all__` contains all symbols defined in the module).
- By default only applies to packages (i.e.`__init__.py` files).
- Generally if something is not in `__all__` it should not be used outside the module, functions, classes and constants
  that are not exported should be given a name with a single leading underscore: `_private`

### `pyproject-validate-version`

Verifies that the version in `pyproject.toml` adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/).

Details: <https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions>

### `pyproject-update-deps`

**NOTE:** THIS HOOK IS SET TO MANUAL BY DEFAULT. RUN VIA

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

### `pyright-concise`

Runs the following wrapper around `pyright`:

```bash
script -c "pyright $*" /dev/null | grep --color=never -Po "(?<=$PWD/)(.*:.*)"
```

This produces a concise output similar to `mypy --no-pretty --no-error-summary --hide-error-end --hide-error-context`.

## pygrep-based hooks

### `python-no-blanket-type-ignore`

A modified version of the hook at <https://github.com/pre-commit/pygrep-hooks>.

- allows `# type: ignore` at the top of the file to ignore the whole file (cf. <https://github.com/python/mypy/issues/964>)
- colon after "type" non-optional.

### `python-no-builtin-eval`

A modified version of the hook at <https://github.com/pre-commit/pygrep-hooks>.

- allows `<obj>.eval`, e.g. `pandas.eval`.
- only blank `eval(` and `builtins.eval(` are forbidden.

### `check-separator-length`

Tests that "line-break" comments terminate at column 88.

```python
# region implementation -------------------- <-- should terminate at column 88
```

### `python-consider-using-raw-string`

Hints that triple quoted strings should be raw strings (convention).
Ignores triple quoted f-strings.

### `python-rename-axes-axis`

Makes sure function signatures use `axis=` instead of `axes=` (numpy convention).

## $\LaTeX$ Hooks

### `chktex` ($\LaTeX$ linter)

**Default configuration:** All checks are enabled except for

- `1`: *Command terminated with space.* (wrong advice[^warn1])
- `3`: *Enclose previous parentheses with `{}`.* (wrong advice[^warn3])
- `9`: *‘%s’ expected, found ‘%s’.* (interferes with half-open intervals[^warn9])
- `17`: *Number of ‘character’ doesn’t match the number of ‘character’.* (interferes with half-open intervals[^warn17])
- `19`: *You should use "`’`" (ASCII 39) instead of "`’`" (ASCII 180).* (gets confused by unicode[^warn19])
- `21`: *This command might not be intended.* (too many false positives[^warn21])
- `22`: *Comment displayed.* (not useful in the context of `pre-commit`)
- `30`: *Multiple spaces detected in output.*  (not useful when using spaces for indentation)
- `46`: *Use `\(...\)` instead of `$...$`.* (wrong advice[^warn21])

To manually select which checks to enable, add `args`-section to the hook configuration in `.pre-commit-config.yaml`.

**Usage Recommendations:**

- `30`: Consider enabling when using tabs for indentation.
- `41`: Keep enabled, but put `% chktex-file 41` inside `.sty` and `.cls` files.
- `44`: For block-matrices, the `nicematrix` package is recommended. Otherwise, it is suggested to allow individual tables by adding a `% chktex 44` comment after `\begin{tabular}{...}`.

### `lacheck` ($\LaTeX$ linter)

**Note:** `lacheck` does not offer any configuration options.

## WIP Hooks

### `check_naming_convention` (not implemented yet)

Checks that naming conventions are followed. Defaults:

- constants: exported: `UPPERCASE_WITH_UNDERSCORES`, internal: `_UPPERCASE_WITH_UNDERSCORES`, special: `__dunder__`
- functions: exported: `snake_case`, internal: `_snake_case`, special: `__dunder__`
- classes: exported: `PascalCase`, internal: `_PascalCase`, special: `__dunder__`

[//]: # (footnotes)
[^warn1]: <https://tex.stackexchange.com/q/552210>
[^warn3]: <https://tex.stackexchange.com/q/529937>
[^warn9]: <https://tex.stackexchange.com/q/405583>
[^warn17]: <https://tex.stackexchange.com/q/405583>
[^warn19]: <https://github.com/nscaife/linter-chktex/issues/30>
[^warn21]: <https://tex.stackexchange.com/q/473080>
