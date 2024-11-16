# python-match-case-builtins

Checks that builtin shortcuts like `str(name)` is used instead of `str() as name`.
Applies to bool, bytearray, bytes, dict, float, frozenset, int, list, set, str, and tuple.
Note that this may come with a slight performance penalty, but is more readable and concise.

See: <https://peps.python.org/pep-0634/#class-patterns>
