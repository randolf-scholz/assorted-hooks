#!/usr/bin/env python
"""Check to ensure collections.abc is used instead of typing."""


import argparse
import ast
import collections.abc
import sys
import typing
from ast import AST, Attribute, Import, ImportFrom, Name
from collections.abc import Iterator
from pathlib import Path

from assorted_hooks.utils import get_python_files

_METHODS = {
    "AsyncGenerator",
    "AsyncIterable",
    "AsyncIterator",
    "Awaitable",
    "ByteString",
    "Callable",
    "Collection",
    "Container",
    "Coroutine",
    "Generator",
    "Hashable",
    "ItemsView",
    "Iterable",
    "Iterator",
    "KeysView",
    "Mapping",
    "MappingView",
    "MutableMapping",
    "MutableSequence",
    "MutableSet",
    "Reversible",
    "Sequence",
    "Set",
    "Sized",
    "ValuesView",
}

METHODS: set[str] = set(typing.__all__) & set(collections.abc.__all__)

assert METHODS >= _METHODS


def get_top_attributes(tree: AST, /) -> Iterator[Attribute]:
    """Get top attribute nodes."""
    for node in ast.walk(tree):
        if isinstance(node, Attribute) and isinstance(node.value, Name):
            yield node


def get_imports(tree: AST, /) -> Iterator[Import]:
    """Get all import nodes."""
    for node in ast.walk(tree):
        if isinstance(node, Import):
            yield node


def get_import_from(tree: AST, /) -> Iterator[ImportFrom]:
    """Get all import-from nodes."""
    for node in ast.walk(tree):
        if isinstance(node, ImportFrom):
            yield node


def typing_attribute_shadows_abc(node: Attribute, /) -> set[str]:
    """Check if an attribute node shadows an abc attribute."""
    if not isinstance(node.value, Name):
        raise ValueError(f"Expected value type ast.Name, got {type(node.value)=}")

    if node.value.id != "typing":
        return set()
    return {node.attr} if node.attr in METHODS else set()


def typing_import_shadows_abc(node: Import, /) -> set[str]:
    """Check if an import node shadows an abc attribute."""
    shadowed: set[str] = set()
    for thing in node.names:
        if thing.name.startswith("typing.") and thing.name[7:] in METHODS:
            shadowed.add(thing.name[7:])
    return shadowed


def typing_import_from_shadows_abc(node: ImportFrom, /) -> set[str]:
    """Check if an import-from node shadows an abc attribute."""
    if node.module != "typing":
        return set()
    return {thing.name for thing in node.names if thing.name in METHODS}


def check_file(fname: str | Path, /) -> bool:
    """Check a single file."""
    with open(fname, "r") as f:
        tree = ast.parse(f.read())

    passed = True
    node: AST

    for node in get_imports(tree):
        if shadowed := typing_import_shadows_abc(node):
            passed = False
            for method in shadowed:
                print(
                    f"{fname!s}:{node.lineno}:"
                    f" Use collections.abc.{method} instead of typing.{method}"
                )

    for node in get_import_from(tree):
        if shadowed := typing_import_from_shadows_abc(node):
            passed = False
            for method in shadowed:
                print(
                    f"{fname!s}:{node.lineno}:"
                    f" Use collections.abc.{method} instead of typing.{method}"
                )

    for node in get_top_attributes(tree):
        if shadowed := typing_attribute_shadows_abc(node):
            passed = False
            for method in shadowed:
                print(
                    f"{fname!s}:{node.lineno}:"
                    f" Use collections.abc.{method} instead of typing.{method}"
                )

    return passed


def main() -> None:
    """Main program."""
    parser = argparse.ArgumentParser(
        description="Check whether attributes in annotations shadow directly imported symbols.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument("--debug", action="store_true", help="Print debug information.")
    args = parser.parse_args()

    # find all files
    files: list[Path] = get_python_files(args.files)

    if args.debug:
        print("Files:")
        for file in files:
            print(f"  {file!s}:0")

    # apply script to all files
    passed = True
    for file in files:
        passed &= check_file(file)

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
