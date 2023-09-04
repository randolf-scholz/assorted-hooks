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
import logging
import sys
from ast import AST, AsyncFunctionDef, Attribute, Call, ClassDef, FunctionDef, Name
from collections.abc import Collection, Iterator
from pathlib import Path
from typing import TypeAlias

from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)

Func: TypeAlias = FunctionDef | AsyncFunctionDef
"""Type alias for function-defs."""


def get_full_attribute_name(node: Call | Attribute | Name, /) -> str:
    """Get the parent of an attribute node."""
    if isinstance(node, Call):
        assert isinstance(node.func, (Attribute, Name))
        return get_full_attribute_name(node.func)
    if isinstance(node, Attribute):
        assert isinstance(node.value, (Attribute, Name))
        string = get_full_attribute_name(node.value)
        return f"{string}.{node.attr}"

    if not isinstance(node, Name):
        raise ValueError(f"Expected ast.Name, got {type(node)}")

    return node.id


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
    """Get all function that are defined directly inside class bodies."""
    for cls in get_classes(tree):
        for node in cls.body:
            if isinstance(node, Func):
                yield node


def get_funcs_outside_classes(tree: AST, /) -> Iterator[Func]:
    """Get all functions that are nod defined inside class body."""
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
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "overload" in [d.id for d in decorators]


def is_staticmethod(node: Func, /) -> bool:
    """Checks if the func is a staticmethod."""
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "staticmethod" in [d.id for d in decorators]


def is_dunder(node: Func, /) -> bool:
    """Checks if the name is a dunder name."""
    name = node.name
    return name.startswith("__") and name.endswith("__") and name.isidentifier()


def is_private(node: Func, /) -> bool:
    """Checks if the name is a private name."""
    name = node.name
    return name.startswith("_") and not name.startswith("__") and name.isidentifier()


def is_decorated_with(node: Func, name: str, /) -> bool:
    """Checks if the function is decorated with a certain decorator."""
    return name in [get_full_attribute_name(d) for d in node.decorator_list]


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
    ignore_decorators: Collection[str] = (),
    ignore_overloads: bool = True,
    ignore_private: bool = False,
    ignore_wo_pos_only: bool = False,
) -> bool:
    """Check whether the file contains mixed positional and keyword arguments."""
    passed = True

    def is_ignorable(func: Func, /) -> bool:
        """Checks if the func can be ignored."""
        return (
            (ignore_wo_pos_only and not func.args.posonlyargs)
            or (ignore_dunder and is_dunder(func))
            or (ignore_overloads and is_overload(func))
            or (ignore_private and is_private(func))
            or (func.name in ignore_names)
            or any(is_decorated_with(func, name) for name in ignore_decorators)
        )

    with open(fname, "rb") as file:
        tree = ast.parse(file.read(), filename=fname)

    for node in get_funcs_in_classes(tree):
        if is_ignorable(node):
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
                f" Mixed positional and keyword arguments in function."
            )

    for node in get_funcs_outside_classes(tree):
        if is_ignorable(node):
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
        "--ignore-decorators",
        nargs="*",
        type=str,
        default=[],
        help="Ignore all methods/functions with certain decorators. (for example: '@jit.script')",
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
    passed = True
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            passed &= check_file(
                file,
                allow_one=args.allow_one,
                ignore_dunder=args.ignore_dunder,
                ignore_names=args.ignore_names,
                ignore_overloads=args.ignore_overloads,
                ignore_wo_pos_only=args.ignore_without_positional_only,
                ignore_private=args.ignore_private,
                ignore_decorators=args.ignore_decorators,
            )
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
