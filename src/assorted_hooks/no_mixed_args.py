#!/usr/bin/env python
"""Disallow mixed positional and keyword arguments in function-defs."""

__all__ = [
    "check_file",
    "get_functions",
    "has_mixed_args",
    "main",
]

import argparse
import ast
import sys
from pathlib import Path
from typing import Iterator

from assorted_hooks.utils import get_python_files


def get_functions(tree: ast.AST, /) -> Iterator[ast.FunctionDef]:
    """Get all function-defs from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            yield node


def has_mixed_args(node: ast.FunctionDef, /) -> bool:
    """Checks if the node allows mixed po/kwargs."""
    return bool(node.args.args)


def check_file(fname: str | Path, /) -> bool:
    """Check whether the file contains mixed positional and keyword arguments."""
    with open(fname, "rb") as file:
        tree = ast.parse(file.read(), filename=fname)

    passed = True

    for node in get_functions(tree):
        if has_mixed_args(node):
            passed = False
            arg = node.args.args[0]
            print(f"{fname!s}:{arg.lineno}: Mixed positional and keyword arguments.")

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
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument("--debug", action="store_true")
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
        sys.exit("Found mixed positional and keyword arguments.")


if __name__ == "__main__":
    main()
