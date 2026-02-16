# check-dunder-all

Checks that:

- `__all__` is defined in all modules.
- `__all__` is defined at the top of the file.
- `__all__` is only preceded by the module docstring and `__future__` imports.
- `__all__` is defined as a literal list (not tuple, set, etc.)
- `__all__` is not defined multiple times.
- `__all__` is not superfluous (i.e. contains all symbols defined in the module)

## Additional Arguments

- `--warn-missing` / `--no-warn-missing`: Warn if `__all__` is missing.
- `--allow-missing-empty` / `--no-allow-missing-empty`: Allow missing `__all__` if file is essentially empty.
- `--warn-non-literal` / `--no-warn-non-literal`: Check that `__all__` is a literal list of strings.
- `--warn-annotated` / `--no-warn-annotated`: Warn if `__all__` is annotated.
- `--warn-location` / `--no-warn-location`: Warn if `__all__` is not at the top of the file.
- `--warn-superfluous` / `--no-warn-superfluous`: Warn if `__all__` is superfluous.
- `--warn-multiple-definitions` / `--no-warn-multiple-definitions`: Warn if multiple `__all__` definitions are present.
- `--warn-duplicate-keys` / `--no-warn-duplicate-keys`: Warn if `__all__` contains duplicate keys.
- `--ignore-executables`: Allow missing `__all__` in executable files (useful when you mainly want library modules).
- `--debug` / `--no-debug`: Print debug information.
