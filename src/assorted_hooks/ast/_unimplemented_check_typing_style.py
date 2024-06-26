#!/usr/bin/env python
r"""Opinionated style checks related to typing.

NOTE: TypeShed defines open() as:

- `def open(file: file: FileDescriptorOrPath, ...): ...`
   https://github.com/python/typeshed/blob/a094aa09c2aa47721664d3fdef91eda4fac24ebb/stdlib/builtins.pyi#L1553-L1555
- `FileDescriptorOrPath: TypeAlias = int | StrOrBytesPath`
  https://github.com/python/typeshed/blob/a094aa09c2aa47721664d3fdef91eda4fac24ebb/stdlib/_typeshed/__init__.pyi#L221C55
- `StrOrBytesPath: TypeAlias = str | bytes | PathLike[str] | PathLike[bytes]  # stable`
  https://github.com/python/typeshed/blob/a094aa09c2aa47721664d3fdef91eda4fac24ebb/stdlib/_typeshed/__init__.pyi#L146
"""

# IDEA: Suggest TypeAlias for unions over K elements.
# IDEA: Use `str | PathLike[str]` instead of `str | Path`
# IDEA: enable/disable checks automatically based on python version.
# IDEA: prefer typing_extensions over typing.

if __name__ == "__main__":
    raise NotImplementedError
