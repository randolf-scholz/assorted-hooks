# custom pre-commit hooks

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

[python-hooks](#python-hooks) | [pygrep hooks](#pygrep-hooks) | [CHANGELOG](CHANGELOG.md) | [LICENSE](LICENSE)

## Python Hooks

### AST-Based

- [`check-direct-imports`](docs/python/check_direct_imports.md): use directly imported symbols instead of module attributes.\
  **Example:** if both `import ast` and `from ast import AST` are present, use `AST` instead of `ast.AST`.
- [`check-no-mixed-args`](docs/python/check_no_mixed_args.md): ensure no `POSITIONAL_OR_KEYWORD` parameters are used in function definitions.\
  **Example:** use `def f(a, b, /, *, c=1):` instead of `def f(a, b, c=1):`.
- [`check-dunder-all`](docs/python/check_dunder_all.md): ensure `__all__` is defined in all modules and is well-formed.\
  **Example:** `__all__ = ['a', 'b', 'c']`.
- [`check-typing`](docs/python/check_typing.md): AST based linting rules for python type hints.

### Script-Based

⚠️ These hooks may import your code. ⚠️

- [`check-clean-interface`](docs/python/check_clean_interface.md): checks that `dir(module)` is equal to `__all__` for `__init__.py` files. (imports the module)
- [`update-requirements`](docs/python/update_requirements.md): updates `pyproject.toml` requirements to `>=%cur%`, where `%cur%` is the current version present in the local virtual environment.
- [`check-requirements-used`](docs/python/check_requirements_used.md): checks that all declared requirements are used in the codebase (inspects `pyproject.toml`, needs access to local virtual environment).
- [`check-requirements-valid`](docs/python/check_requirements_valid.md): Uses [`pypa/packaging`](https://github.com/pypa/packaging) to check that all requirements are well-formed.
- [`check-requirements-maintained`](docs/python/check_requirements_maintained.md): checks that your requirements have received updates in the last 1000 days.

## Misc. Hooks

- [`check-archived-hooks`](docs/check_archived_hooks.md): Checks your `.pre-commit-config.yaml` for archived repositories.
- [`check-resolved-github-issues`](docs/check_resolved_github_issues.md): Checks code for references to GitHub issues. Queries the GitHub API to check if the issues are resolved.\
  **Note:** By default only checks GitHub urls prefixed with `FIXME:`, can be disabled by changing the `--prefix` regex.
- [`pyright-concise`](docs/pyright_concise.md): runs `pyright` with a concise output formatting.

## pygrep hooks

- [`check-separator-length`](docs/pygrep/check_separator_length.md): checks that "horizontal-rule" comments terminate at column 88.
- [`python-consider-using-raw-string`](docs/pygrep/python_consider_using_raw_string.md): hints that triple quoted strings should be raw strings.
- [`python-rename-axes-axis`](docs/pygrep/python_rename_axes_axis.md): checks that function signatures use `axis=` instead of `axes=`.
- [`python-match-case-builtins`](docs/pygrep/python_match_case_builtins.md): checks that `str(name)` is used instead of `str() as name` in match-case expressions.
- [`python-system-exit`](docs/pygrep/python_system_exit.md): Use `raise SystemExit` instead of `sys.exit()`.
- [`pyarrow-timestamp-seconds`](docs/pygrep/pyarrow_timestamp_seconds.md): flags `timestamp('s')` as a potential bug.

## deprecated hooks

- [`python-no-builtin-eval`](docs/pygrep/python_no_builtin_eval.md): checks that `eval` is not used with a blank string.\
  Use ruff [`S307`](https://docs.astral.sh/ruff/rules/suspicious-eval-usage/) instead.
- [`check-standard-generics`](docs/python/check_standard_generics.md): use `collections.abc` instead of `typing`/`typing_extensions` whenever possible.\
  Use ruff rule [`UP035`](https://docs.astral.sh/ruff/rules/deprecated-import/) instead.\
- [`python-no-blanket-type-ignore`](docs/pygrep/python_no_blanket_type_ignore.md): checks that `# type: ignore` is not used without a reason.
  Use ruff rule [`PGH003`](https://docs.astral.sh/ruff/rules/blanket-type-ignore/) instead.
