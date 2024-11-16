# check-typing

AST based linting rules for python type hints. Default settings are

## Additional Arguments

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
- [ ] `--check-no-return-union-recursive`: Same as `--check-no-return-union`, but checks for `Union` recursively (e.g. disallows `list[int | str]`).
