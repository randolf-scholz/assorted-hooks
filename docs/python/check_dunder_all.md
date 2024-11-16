# check-dunder-all

Checks that:

- `__all__` is defined in all modules.
- `__all__` is defined at the top of the file.
- `__all__` is only preceded by the module docstring and `__future__` imports.
- `__all__` is defined as a literal list (not tuple, set, etc.)
- `__all__` is not defined multiple times.
- `__all__` is not superfluous (i.e. contains all symbols defined in the module)

## Additional Arguments
