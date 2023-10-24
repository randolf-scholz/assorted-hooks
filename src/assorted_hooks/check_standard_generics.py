#!/usr/bin/env python
"""Check to ensure collections.abc is used instead of typing."""

__all__ = [
    "REPLACEMENTS",
    "check_file",
    "get_deprecated_aliases",
    "main",
]

import argparse
import ast
import collections.abc
import logging
import sys
import typing
from ast import AST, Attribute, Import, ImportFrom, Name
from pathlib import Path
from typing import Final

from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)

REPLACEMENTS: Final[dict[str, str]] = {
    # fmt: off
    # builtins
    "typing.Dict"                : "dict",
    "typing.FrozenSet"           : "frozenset",
    "typing.List"                : "list",
    "typing.Set"                 : "set",
    "typing.Text"                : "str",
    "typing.Tuple"               : "tuple",
    "typing.Type"                : "type",
    # collections
    "typing.Deque"               : "collections.deque",
    "typing.DefaultDict"         : "collections.defaultdict",
    "typing.OrderedDict"         : "collections.OrderedDict",
    "typing.ChainMap"            : "collections.ChainMap",
    "typing.Counter"             : "collections.Counter",
    # async
    "typing.Awaitable"           : "collections.abc.Awaitable",
    "typing.Coroutine"           : "collections.abc.Coroutine",
    "typing.AsyncIterable"       : "collections.abc.AsyncIterable",
    "typing.AsyncIterator"       : "collections.abc.AsyncIterator",
    "typing.AsyncGenerator"      : "collections.abc.AsyncGenerator",
    # abcs
    "typing.AbstractSet"         : "collections.abc.Set",
    "typing.ByteString"          : "collections.abc.ByteString",
    "typing.Callable"            : "collections.abc.Callable",
    "typing.Collection"          : "collections.abc.Collection",
    "typing.Container"           : "collections.abc.Container",
    "typing.Generator"           : "collections.abc.Generator",
    "typing.Hashable"            : "collections.abc.Hashable",
    "typing.Iterable"            : "collections.abc.Iterable",
    "typing.Iterator"            : "collections.abc.Iterator",
    "typing.Mapping"             : "collections.abc.Mapping",
    "typing.MutableMapping"      : "collections.abc.MutableMapping",
    "typing.MutableSequence"     : "collections.abc.MutableSequence",
    "typing.MutableSet"          : "collections.abc.MutableSet",
    "typing.Reversible"          : "collections.abc.Reversible",
    "typing.Sequence"            : "collections.abc.Sequence",
    "typing.Sized"               : "collections.abc.Sized",
    # views
    "typing.MappingView"         : "collections.abc.MappingView",
    "typing.KeysView"            : "collections.abc.KeysView",
    "typing.ItemsView"           : "collections.abc.ItemsView",
    "typing.ValuesView"          : "collections.abc.ValuesView",
    # context
    "typing.ContextManager"      : "contextlib.AbstractContextManager",
    "typing.AsyncContextManager" : "contextlib.AbstractAsyncContextManager",
    # regex
    "typing.Pattern"             : "re.Pattern",
    "typing.re.Pattern"          : "re.Pattern",
    "typing.Match"               : "re.Match",
    "typing.re.Match"            : "re.Match",
    # fmt: on
}

KEYS: Final[frozenset[str]] = frozenset(REPLACEMENTS.keys())

# validate replacements
METHODS: Final[set[str]] = set(typing.__all__) & set(collections.abc.__all__)
assert all(f"typing.{method}" in REPLACEMENTS for method in METHODS)


def get_deprecated_aliases(node: AST, /) -> frozenset[str]:
    """Get all deprecated aliases from a node."""
    match node:
        case Attribute(attr=attr, value=Name(id=name)):
            return KEYS & {f"{name}.{attr}"}
        case Import(names=names):
            return KEYS & {imp.name for imp in names}
        case ImportFrom(module=module, names=names):
            return KEYS & {f"{module}.{imp.name}" for imp in names}
        case _:
            return frozenset()


def check_file(fname: str | Path, /) -> bool:
    """Check a single file."""
    passed = True

    with open(fname, "r", encoding="utf8") as file:
        tree = ast.parse(file.read())

    for node in ast.walk(tree):
        for alias in get_deprecated_aliases(node):
            passed = False
            loc = f"{fname!s}:{node.lineno}"
            print(f"{loc}: Use {REPLACEMENTS[alias]!r} instead of {alias!r}.")

    return passed


def main() -> None:
    """Main program."""
    parser = argparse.ArgumentParser(
        description="Use standard generics (PEP-585): typing.Sequence -> abc.Sequence, typing.List -> list.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument(
        "--use-never",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Hint to use typing.Never instead of typing.NoReturn.",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Print debug information.",
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        __logger__.debug("args: %s", vars(args))

    if args.use_never:
        REPLACEMENTS["typing.NoReturn"] = "typing.Never"

    # find all files
    files: list[Path] = get_python_files(args.files)

    # apply script to all files
    passed = True
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            passed &= check_file(file)
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
