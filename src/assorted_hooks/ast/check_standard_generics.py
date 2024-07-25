#!/usr/bin/env python
r"""Check to ensure collections.abc is used instead of typing."""

__all__ = [
    # Constants
    "REPLACEMENTS",
    "METHODS",
    "BAD_ALIASES",
    # Functions
    "check_file",
    "main",
]

import argparse
import ast
import logging
import sys
import typing
from collections import abc
from pathlib import Path
from typing import Final

from assorted_hooks.ast.ast_utils import yield_aliases
from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)

REPLACEMENTS: dict[str, str] = {
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
}  # fmt: skip

# add typing_extensions aliases
REPLACEMENTS |= {
    key.replace("typing", "typing_extensions"): value
    for key, value in REPLACEMENTS.items()
}

BAD_ALIASES: Final[frozenset[str]] = frozenset(REPLACEMENTS.keys())

# validate replacements
METHODS: Final[set[str]] = set(typing.__all__) & set(abc.__all__)
if any(f"typing.{method}" not in REPLACEMENTS for method in METHODS):
    raise ValueError("Missing replacements for standard generics.")


def check_file(filepath: str | Path, /) -> int:
    r"""Check a single file."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    fname = str(path)
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=fname)

    for alias in yield_aliases(tree):
        name, lineno = alias.name, alias.lineno
        if name in BAD_ALIASES:
            violations += 1
            replacement = REPLACEMENTS[name]
            print(f"{fname}:{lineno}: Use {replacement!r} instead of {name!r}.")

    return violations


def main() -> None:
    r"""Main program."""
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
    violations = 0
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            violations += check_file(file)
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
