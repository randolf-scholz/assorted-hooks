# check-no-mixed-args

Checks that all function definitions allow no `POSITIONAL_OR_KEYWORD` arguments.
Only `POSITIONAL_ONLY`, `KEYWORD_ONLY`, `VAR_POSITIONAL` and `VAR_KEYWORD` are allowed.
Excludes are lambda functions, functions inside docstrings, and the arguments `self` and `cls`.

## Additional Arguments

- `--allow-one`: allows a single `POSITIONAL_OR_KEYWORD` argument. This is often ok, since there is no ambiguity of the order of arguments. (default: `False`)
- `--allow-two`: allows two `POSITIONAL_OR_KEYWORD` arguments. (default: `False`)
- `--ignore-dunder`: skip function defs that are dunder methods (default: `False`)
- `--ignore-private`: skip function defs that are private (default: `False`)
- `--ignore-overloads`: skip function defs that are overloads of other function defs. (default: `True`)
- `--ignore-without-positional-only`: skip function defs that don't have any `POSITIONAL_ONLY` arguments. (default: `False`)
- `--ignore-names *names`: skip function defs with specific names (default: `[]`)
- `--ignore-decorators *names`: skip function defs with specific decorators (default: `[]`)
