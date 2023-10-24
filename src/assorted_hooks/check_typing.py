#!/usr/bin/env python
# type: ignore
# FIXME: https://github.com/python/mypy/issues/11673
"""Disallow mixed positional and keyword arguments in function-defs."""

__all__ = [
    "check_file",
    "main",
]

import argparse
import ast
import logging
import sys
from ast import AST, AsyncFunctionDef, BinOp, BitOr, FunctionDef, Name, Subscript
from collections.abc import Iterator
from pathlib import Path
from typing import TypeAlias

from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)

Func: TypeAlias = FunctionDef | AsyncFunctionDef
"""Type alias for function-defs."""


def is_union(node: AST, /) -> bool:
    """True if the return node is a union."""
    match node:
        case Subscript(value=Name(id="Union")):
            return True
        case BinOp(op=BitOr()):
            return True
        case _:
            return False


def has_union(tree: AST, /) -> bool:
    """True if the return node is a union."""
    for node in ast.walk(tree):
        if is_union(node):
            return True
    return False


def get_function_defs(tree: AST, /) -> Iterator[Func]:
    """Get all return nodes."""
    for node in ast.walk(tree):
        if isinstance(node, Func):
            yield node


def check_file(fname: str | Path, /, *, recursive: bool = True) -> int:
    """Check whether the file contains mixed positional and keyword arguments."""
    violations = 0

    with open(fname, "rb") as file:
        tree = ast.parse(file.read(), filename=fname)

    for node in get_function_defs(tree):
        if node.returns is None:
            continue
        if is_union(node.returns):
            violations += 1
            print(f"{fname!s}:{node.lineno}:" f" Do not return union type!")
        if recursive and has_union(node.returns):
            violations += 1
            print(f"{fname!s}:{node.lineno}:" f" Do not return union type!")

    return violations


def main() -> None:
    """Main program."""
    parser = argparse.ArgumentParser(
        description="Check for disallowing positional_or_keyword arguments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Recursively check for unions.",
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
            violations += check_file(
                file,
                recursive=args.recursive,
            )
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-'*79}\nFound {violations} violations.")
        sys.exit(1)


if __name__ == "__main__":
    main()
