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
    "is_dunder",
    "is_overload",
    "is_private",
    "is_staticmethod",
    "main",
    "method_has_mixed_args",
]

import argparse
import ast
import sys
from ast import AST, AsyncFunctionDef, ClassDef, FunctionDef
from collections.abc import Collection, Iterator
from pathlib import Path
from typing import TypeAlias

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


def is_dunder(node: Func, /) -> bool:
    """Checks if the name is a dunder name."""
    name = node.name
    return name.startswith("__") and name.endswith("__") and name.isidentifier()


def is_private(node: Func, /) -> bool:
    """Checks if the name is a private name."""
    name = node.name
    return name.startswith("_") and not name.startswith("__") and name.isidentifier()


def method_has_mixed_args(node: Func, /, *, allow_one: bool = False) -> bool:
    """Checks if the method allows mixed po/kwargs."""
    if is_staticmethod(node):
        return func_has_mixed_args(node, allow_one=allow_one)

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
    ignore_dunder: bool = False,
    ignore_names: Collection[str] = (),
    ignore_overloads: bool = True,
    ignore_private: bool = False,
    ignore_wo_pos_only: bool = False,
) -> bool:
    """Check whether the file contains mixed positional and keyword arguments."""
    with open(fname, "rb") as file:
        tree = ast.parse(file.read(), filename=fname)

    passed = True

    for node in get_funcs_in_classes(tree):
        if (
            (ignore_wo_pos_only and not node.args.posonlyargs)
            or (ignore_overloads and is_overload(node))
            or (node.name in ignore_names)
            or (ignore_dunder and is_dunder(node))
            or (ignore_private and is_private(node))
        ):
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
        if (
            (ignore_wo_pos_only and not node.args.posonlyargs)
            or (ignore_overloads and is_overload(node))
            or (node.name in ignore_names)
            or (ignore_dunder and is_dunder(node))
            or (ignore_private and is_private(node))
        ):
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
        type=str,
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
        "--ignore-names",
        nargs="*",
        type=str,
        default=[],
        help="Ignore all methods/functions with these names. (for example: 'forward')",
    )
    parser.add_argument(
        "--ignore-dunder",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Ignore all dunder methods/functions (e.g. __init__).",
    )
    parser.add_argument(
        "--ignore-private",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Ignore all private methods/functions (e.g. _method).",
    )
    parser.add_argument(
        "--ignore-overloads",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore FunctionDefs that are @overload decorated..",
    )
    parser.add_argument(
        "--ignore-without-positional-only",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Skip FunctionDefs without positional-only arguments.",
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
        passed &= check_file(
            file,
            allow_one=args.allow_one,
            ignore_dunder=args.ignore_dunder,
            ignore_names=args.ignore_names,
            ignore_overloads=args.ignore_overloads,
            ignore_wo_pos_only=args.ignore_without_positional_only,
            ignore_private=args.ignore_private,
        )

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
