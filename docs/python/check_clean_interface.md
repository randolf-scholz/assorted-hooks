# check-clean-interface

- Checks that `dir(module)` is equal to `__all__` (i.e. that `__all__` contains all symbols defined in the module).
- By default only applies to packages (i.e.`__init__.py` files).
- Generally if something is not in `__all__` it should not be used outside the module, functions, classes and constants
  that are not exported should be given a name with a single leading underscore: `_private`

## Additional Arguments
