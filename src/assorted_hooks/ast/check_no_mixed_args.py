#!/usr/bin/env python
# FIXME: https://github.com/python/mypy/issues/11673
r"""Disallow mixed positional and keyword arguments in function-defs."""

__all__ = [
    # Types
    "Func",
    # Functions
    "check_file",
    # "get_mixed_args_function",
    "get_classes",
    "get_full_attribute_name",
    "get_funcs_in_classes",
    "get_funcs_outside_classes",
    "get_functions",
    "is_decorated_with",
    "is_dunder",
    "is_overload",
    "is_private",
    "is_staticmethod",
    "main",
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
r"""Type alias for function-defs."""


def get_full_attribute_name(node: AST, /) -> str:
    r"""Get the parent of an attribute node."""
    match node:
        case Call(func=Attribute() | Name() as func):
            return get_full_attribute_name(func)
        case Attribute(value=Attribute() | Name() as value, attr=attr):
            string = get_full_attribute_name(value)
            return f"{string}.{attr}"
        case Name(id=node_id):
            return node_id
        case _:
            raise TypeError(f"Expected Call, Attribute or Name, got {type(node)=!r}")


def get_functions(tree: AST, /) -> Iterator[Func]:
    r"""Get all function-defs from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, Func):  # type: ignore[misc, arg-type]
            yield node  # type: ignore[misc]


def get_classes(tree: AST, /) -> Iterator[ClassDef]:
    r"""Get all class-defs from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, ClassDef):
            yield node


def get_funcs_in_classes(tree: AST, /) -> Iterator[Func]:
    r"""Get all function that are defined directly inside class bodies."""
    for cls in get_classes(tree):
        for node in cls.body:
            if isinstance(node, Func):  # type: ignore[misc, arg-type]
                yield node  # type: ignore[misc]


def get_funcs_outside_classes(tree: AST, /) -> Iterator[Func]:
    r"""Get all functions that are nod defined inside class body."""
    funcs_in_classes: set[AST] = set()

    for node in ast.walk(tree):
        match node:
            case ClassDef(body=body):
                funcs_in_classes.update(
                    child
                    for child in body
                    if isinstance(child, Func)  # type: ignore[misc, arg-type]
                )
            # FIXME: https://github.com/python/cpython/issues/106246
            case FunctionDef() | AsyncFunctionDef():
                if node not in funcs_in_classes:
                    yield node


# def get_mixed_args_function(node: Func, /) -> list[ast.arg]:
#     r"""Returns the mixed args of a function (not method)."""
#     return node.args.args


def is_overload(node: Func, /) -> bool:
    r"""Checks if the func is an overload."""
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "overload" in [d.id for d in decorators]


def is_staticmethod(node: Func, /) -> bool:
    r"""Checks if the func is a staticmethod."""
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "staticmethod" in [d.id for d in decorators]


def is_dunder(node: Func, /) -> bool:
    r"""Checks if the name is a dunder name."""
    name = node.name
    return name.startswith("__") and name.endswith("__") and name.isidentifier()


def is_private(node: Func, /) -> bool:
    r"""Checks if the name is a private name."""
    name = node.name
    return name.startswith("_") and not name.startswith("__") and name.isidentifier()


def is_decorated_with(node: Func, name: str, /) -> bool:
    r"""Checks if the function is decorated with a certain decorator."""
    return name in [get_full_attribute_name(d) for d in node.decorator_list]


def check_file(
    filepath: str | Path,
    /,
    *,
    allow_one: bool = False,
    allow_two: bool = False,
    ignore_dunder: bool = False,
    ignore_names: Collection[str] = (),
    ignore_decorators: Collection[str] = (),
    ignore_overloads: bool = True,
    ignore_private: bool = False,
    ignore_wo_pos_only: bool = False,
) -> int:
    r"""Check whether the file contains mixed positional and keyword arguments."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    fname = str(path)
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=fname)

    num_allowed_args = 2 if allow_two else 1 if allow_one else 0

    def is_ignorable(func: Func, /) -> bool:
        r"""Checks if the func can be ignored."""
        return (
            (ignore_wo_pos_only and not func.args.posonlyargs)
            or (ignore_dunder and is_dunder(func))
            or (ignore_overloads and is_overload(func))
            or (ignore_private and is_private(func))
            or (func.name in ignore_names)
            or any(is_decorated_with(func, name) for name in ignore_decorators)
        )

    for node in get_funcs_in_classes(tree):
        if is_ignorable(node):
            continue
        args = (
            node.args.args
            if is_staticmethod(node) or node.args.posonlyargs
            else node.args.args[1:]  # exclude self/cls
        )

        if len(args) > num_allowed_args:
            violations += 1
            try:
                arg = node.args.args[0]
            except IndexError as exc:
                raise RuntimeError(
                    f'"{fname}:{node.lineno}" Something went wrong. {vars(node)=}'
                ) from exc
            print(
                f"{fname}:{arg.lineno}:"
                f" Mixed positional and keyword arguments in function."
            )

    for node in get_funcs_outside_classes(tree):
        if is_ignorable(node):
            continue
        if len(node.args.args) > num_allowed_args:
            violations += 1
            try:
                arg = node.args.args[0]
            except IndexError as exc:
                raise RuntimeError(
                    f'"{fname}:{node.lineno}" Something went wrong. {vars(node)=}'
                ) from exc
            print(
                f"{fname}:{arg.lineno}:"
                f" Mixed positional and keyword arguments in function."
            )

    return violations


def main() -> None:
    r"""Main program."""
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
        help="Allows a single positional_or_keyword argument.",
    )
    parser.add_argument(
        "--allow-two",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Allows two positional_or_keyword arguments.",
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
        default=False,
        help="Ignore FunctionDefs that are @overload decorated..",
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
        default=True,
        help="Ignore all private methods/functions (e.g. _method).",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Print debug information.",
    )
    args = parser.parse_args()

    if args.allow_one and args.allow_two:
        raise ValueError(
            "Cannot allow both one and two positional_or_keyword arguments."
        )

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
                allow_one=args.allow_one,
                allow_two=args.allow_two,
                ignore_dunder=args.ignore_dunder,
                ignore_names=args.ignore_names,
                ignore_overloads=args.ignore_overloads,
                ignore_wo_pos_only=args.ignore_without_positional_only,
                ignore_private=args.ignore_private,
                ignore_decorators=args.ignore_decorators,
            )
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
