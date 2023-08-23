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
    "get_attributes",
    "get_full_attribute_parent",
    "get_imported_symbols",
    "get_imported_attributes",
    "check_file",
    "main",
]


import argparse
import ast
import sys
from ast import AST, Attribute, Name
from collections.abc import Iterator
from pathlib import Path

from assorted_hooks.utils import get_python_files


def get_attributes(tree: AST, /) -> Iterator[Attribute]:
    """Get all attribute nodes."""
    for node in ast.walk(tree):
        if isinstance(node, Attribute):
            yield node


def get_full_attribute_parent(node: Attribute | Name, /) -> tuple[Name, str]:
    """Get the parent of an attribute node."""
    if isinstance(node, Attribute):
        if not isinstance(node.value, Attribute | Name):
            raise ValueError(
                f"{node.lineno}: Expected Attribute or Name, got {type(node.value)}"
            )
        parent, string = get_full_attribute_parent(node.value)
        return parent, f"{string}.{node.attr}"

    if not isinstance(node, Name):
        raise ValueError(f"Expected ast.Name, got {type(node)}")

    return node, node.id


def get_imported_symbols(tree: AST, /) -> dict[str, str]:
    """Get all imported symbols."""
    imported_symbols = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_symbols[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module
            if module_name is not None:
                for alias in node.names:
                    full_name = f"{module_name}.{alias.name}"
                    imported_symbols[alias.asname or alias.name] = full_name

    return imported_symbols


def get_imported_attributes(tree: AST, /) -> Iterator[tuple[Attribute, Name, str]]:
    """Finds attributes that can be replaced by directly imported symbols."""
    imported_symbols = get_imported_symbols(tree)

    for node in get_attributes(tree):
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


def check_file(file_path: Path, /, *, debug: bool = False) -> bool:
    """Finds shadowed attributes in a file."""
    # Your code here
    with open(file_path, "r") as file:
        tree = ast.parse(file.read())

    # find all violations
    node: Attribute = NotImplemented
    for node, _, string in get_imported_attributes(tree):
        print(
            f"{file_path!s}:{node.lineno!s}"
            f" use directly imported {node.attr!r} instead of {string!r}"
        )
    passed = node is NotImplemented

    if not passed and debug:
        imported_symbols = get_imported_symbols(tree)
        pad = " " * 4
        max_key_len = max(len(key) for key in imported_symbols.keys())
        print(pad, "Imported symbols:")
        for key, value in imported_symbols.items():
            print(2 * pad, f"{key:{max_key_len}} -> {value}")

    return passed


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

    # find all files
    files: list[Path] = get_python_files(args.files)

    if args.debug:
        print("Files:")
        for file in files:
            print(f"  {file!s}:0")

    # apply script to all files
    passed = True
    for file in files:
        passed &= check_file(file, debug=args.debug)

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
