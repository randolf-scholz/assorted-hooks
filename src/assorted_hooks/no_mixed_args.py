#!/usr/bin/env python
# type: ignore
# FIXME: https://github.com/python/mypy/issues/11673
"""Disallow mixed positional and keyword arguments in function-defs."""

__all__ = [
    "check_file",
    "func_has_mixed_args",
    "get_classes",
    "get_funcs_in_classes",
    "get_funcs_outside_classes",
    "get_functions",
    "is_overload",
    "is_staticmethod",
    "main",
    "method_has_mixed_args",
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


def func_has_mixed_args(node: Func, /, *, allow_one: bool = False) -> bool:
    """Checks if the func allows mixed po/kwargs."""
    return len(node.args.args) > allow_one


def is_overload(node: Func, /) -> bool:
    """Checks if the func is an overload."""
    decorators = (d for d in node.decorator_list if isinstance(d, ast.Name))
    return "overload" in [d.id for d in decorators]


def is_staticmethod(node: Func, /) -> bool:
    """Checks if the func is a staticmethod."""
    decorators = (d for d in node.decorator_list if isinstance(d, ast.Name))
    return "staticmethod" in [d.id for d in decorators]


def method_has_mixed_args(node: Func, /, *, allow_one: bool = False) -> bool:
    """Checks if the method allows mixed po/kwargs."""
    if is_staticmethod(node):
        return func_has_mixed_args(node)

    po_args = node.args.posonlyargs
    args = node.args.args

    if not po_args and not args:
        raise ValueError(
            f"Unreachable? Method has neither PO-args nor args"
            f"but is no staticmethod?? {vars(node)=}"
        )

    if len(args) <= (1 + allow_one) and not po_args:
        return False

    return len(args) > allow_one


def check_file(
    fname: str | Path,
    /,
    *,
    allow_one: bool = False,
    skip_non_po: bool = False,
    ignore_overloads: bool = True,
) -> bool:
    """Check whether the file contains mixed positional and keyword arguments."""
    with open(fname, "rb") as file:
        tree = ast.parse(file.read(), filename=fname)

    passed = True

    for node in get_funcs_in_classes(tree):
        if skip_non_po and not node.args.posonlyargs:
            continue
        if ignore_overloads and is_overload(node):
            continue
        if method_has_mixed_args(node, allow_one=allow_one):
            passed = False
            try:
                arg = node.args.args[0]
            except IndexError as exc:
                raise RuntimeError(
                    f'"{fname!s}:{node.lineno}" Something went wrong.' f" {vars(node)=}"
                ) from exc

            print(
                f"{fname!s}:{arg.lineno}:"
                f" Mixed positional and keyword arguments in method."
            )

    for node in get_funcs_outside_classes(tree):
        if skip_non_po and not node.args.posonlyargs:
            continue
        if ignore_overloads and is_overload(node):
            continue
        if func_has_mixed_args(node, allow_one=allow_one):
            passed = False
            try:
                arg = node.args.args[0]
            except IndexError as exc:
                raise RuntimeError(
                    f'"{fname!s}:{node.lineno}" Something went wrong.' f" {vars(node)=}"
                ) from exc
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
    parser.add_argument(
        "--allow-one",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Allows a single positional_or_keyword argument (only applies when no PO).",
    )
    parser.add_argument(
        "--ignore-without-positional-only",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Skip FunctionDefs without positional-only arguments.",
    )
    parser.add_argument(
        "--ignore-overloads",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore FunctionDefs that are @overload decorated..",
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
        passed &= check_file(
            file,
            allow_one=args.allow_one,
            skip_non_po=args.ignore_without_positional_only,
            ignore_overloads=args.ignore_overloads,
        )

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
