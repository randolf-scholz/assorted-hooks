#!/usr/bin/env python
# type: ignore
# FIXME: https://github.com/python/mypy/issues/11673
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
from ast import AST, AsyncFunctionDef, ClassDef, FunctionDef
from pathlib import Path
from typing import Iterator, TypeAlias

from assorted_hooks.utils import get_python_files

Func: TypeAlias = FunctionDef | AsyncFunctionDef
"""Type alias for function-defs."""


def get_functions(tree: AST, /) -> Iterator[Func]:
    """Get all function-defs from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, Func):
            yield node


def get_classes(tree: AST, /) -> Iterator[ClassDef]:
    """Get all class-defs from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, ClassDef):
            yield node


def get_funcs_in_classes(tree: AST, /) -> Iterator[Func]:
    """Get all function-defs from the tree."""
    for cls in get_classes(tree):
        for node in cls.body:
            if isinstance(node, Func):
                yield node


def get_funcs_outside_classes(tree: AST, /) -> Iterator[Func]:
    """Get all function-defs from the tree."""
    nodes_in_classes: set[AST] = set()

    for node in ast.walk(tree):
        if isinstance(node, ClassDef):
            for child in node.body:
                if isinstance(child, Func):
                    nodes_in_classes.add(child)
        if isinstance(node, Func):
            if node not in nodes_in_classes:
                yield node


def func_has_mixed_args(node: Func, /) -> bool:
    """Checks if the func allows mixed po/kwargs."""
    return bool(node.args.args)


def method_has_mixed_args(node: Func, /) -> bool:
    """Checks if the method allows mixed po/kwargs."""
    decorators = (d for d in node.decorator_list if isinstance(d, ast.Name))
    if "staticmethod" in [d.id for d in decorators]:
        return func_has_mixed_args(node)

    if not node.args.posonlyargs and not node.args.args:
        raise ValueError(
            f"Unreachable? Method has neither PO-args nor args"
            f"but is no staticmethod?? {vars(node)=}"
        )

    if node.args.posonlyargs and not node.args.args:
        # if there are any pos-only args, then the first arg must be self/cls
        return False

    if not node.args.posonlyargs and len(node.args.args) == 1:
        return False

    return True


def has_mixed_args(node: Func, /) -> bool:
    """Checks if the node allows mixed po/kwargs."""
    match len(node.args.args):
        case 0:
            return False
        case 1:
            arg = node.args.args[0]
            if arg.arg in ("self", "cls"):
                return False
            return True
        case _:
            return True


def check_file(fname: str | Path, /) -> bool:
    """Check whether the file contains mixed positional and keyword arguments."""
    with open(fname, "rb") as file:
        tree = ast.parse(file.read(), filename=fname)

    passed = True

    # for node in get_functions(tree):
    #     if has_mixed_args(node):
    #         passed = False
    #         arg = node.args.args[0]
    #         print(f"{fname!s}:{arg.lineno}: Mixed positional and keyword arguments.")

    for node in get_funcs_in_classes(tree):
        if method_has_mixed_args(node):
            passed = False
            arg = node.args.args[0]
            print(
                f"{fname!s}:{arg.lineno}:"
                f" Mixed positional and keyword arguments in method."
            )

    for node in get_funcs_outside_classes(tree):
        if func_has_mixed_args(node):
            passed = False
            arg = node.args.args[0]
            print(
                f"{fname!s}:{arg.lineno}:"
                f" Mixed positional and keyword arguments in function."
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
