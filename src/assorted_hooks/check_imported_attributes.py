#!/usr/bin/env python
"""Check whether attributes in annotations shadow directly imported symbols.

Example:
    >>> import collections.abc as abc
    >>> from collections.abc import Sequence
    >>>
    >>> def foo(x: abc.Sequence) -> abc.Sequence:
    >>>     return x

    Would raise an error because `pd.DataFrame` shadows directly imported `DataFrame`.
"""

__all__ = [
    "get_pure_attributes",
    "get_full_attribute_parent",
    "get_imported_symbols",
    "get_imported_attributes",
    "check_file",
    "main",
]


import argparse
import ast
import logging
import sys
from ast import AST, Attribute, Name
from collections.abc import Iterator
from pathlib import Path
from typing import TypeGuard

from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)


def is_pure_attribute(node: AST, /) -> TypeGuard[Attribute]:
    """Check whether a node is a pure attribute."""
    match node:
        case Attribute(value=value):
            return isinstance(value, Name) or is_pure_attribute(value)
        case _:
            return False


def get_pure_attributes(tree: AST, /) -> Iterator[Attribute]:
    """Get all nodes that consist only of attributes."""
    for node in ast.walk(tree):
        if is_pure_attribute(node):
            yield node


def get_full_attribute_parent(node: Attribute | Name, /) -> tuple[Name, str]:
    """Get the parent of an attribute node."""
    match node:
        case Attribute(value=Attribute() | Name() as value, attr=attr):
            parent, string = get_full_attribute_parent(value)
            return parent, f"{string}.{attr}"
        case Name(id=name):
            return node, name
        case _:
            raise TypeError(f"Expected Attribute or Name, got {type(node)=!r}")


def get_imported_symbols(tree: AST, /) -> dict[str, str]:
    """Get all imported symbols."""
    imported_symbols = {}

    for node in ast.walk(tree):
        match node:
            case ast.Import(names=names):
                for alias in names:
                    imported_symbols[alias.asname or alias.name] = alias.name
            case ast.ImportFrom(module=module, names=names) if module is not None:
                for alias in names:
                    full_name = f"{module}.{alias.name}"
                    imported_symbols[alias.asname or alias.name] = full_name

    return imported_symbols


def get_imported_attributes(tree: AST, /) -> Iterator[tuple[Attribute, Name, str]]:
    """Finds attributes that can be replaced by directly imported symbols."""
    imported_symbols = get_imported_symbols(tree)

    for node in get_pure_attributes(tree):
        if node.attr in imported_symbols:
            # parent = get_full_attribute_string(node)
            parent, string = get_full_attribute_parent(node)

            head, tail = string.split(".", maxsplit=1)
            assert head == parent.id

            # e.g. DataFrame -> pandas.DataFrame
            matched_symbol = imported_symbols[node.attr]
            is_match = matched_symbol == string

            # need to check if parent is imported as well to catch pd.DataFrame
            if parent.id in imported_symbols:
                parent_alias = imported_symbols[parent.id]  # e.g. pd -> pandas
                is_match |= matched_symbol == f"{parent_alias}.{tail}"

            if is_match:
                yield node, parent, string


def check_file(file_path: Path, /, *, debug: bool = False) -> int:
    """Finds shadowed attributes in a file."""
    violations = 0

    # Your code here
    with open(file_path, "r", encoding="utf8") as file:
        tree = ast.parse(file.read())

    # find all violations
    for node, _, string in get_imported_attributes(tree):
        violations += 1
        print(
            f"{file_path!s}:{node.lineno!s}"
            f" use directly imported {node.attr!r} instead of {string!r}"
        )

    if violations and debug:
        imported_symbols = get_imported_symbols(tree)
        pad = " " * 4
        max_key_len = max(map(len, imported_symbols), default=0)
        print(pad, "Imported symbols:")
        for key, value in imported_symbols.items():
            print(2 * pad, f"{key:{max_key_len}} -> {value}")

    return violations


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Checks that Bar is used instead of foo.Bar if both foo and Bar are imported.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
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

    # find all files
    files: list[Path] = get_python_files(args.files)

    # apply script to all files
    violations = 0
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            violations += check_file(file, debug=args.debug)
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-'*79}\nFound {violations} violations.")
        sys.exit(1)


if __name__ == "__main__":
    main()
