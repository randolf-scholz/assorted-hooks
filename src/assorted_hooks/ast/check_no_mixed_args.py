#!/usr/bin/env python
r"""Disallow mixed positional and keyword arguments in function-defs."""

__all__ = [
    # Functions
    "check_file",
    "main",
]

import argparse
import ast
import logging
import sys
from collections.abc import Collection
from pathlib import Path

from assorted_hooks.ast.ast_utils import (
    Func,
    is_decorated_with,
    is_dunder,
    is_overload,
    is_private,
    is_staticmethod,
    yield_funcs_in_classes,
    yield_funcs_outside_classes,
)
from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)


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
    filename = str(path)
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=filename)

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

    for node in yield_funcs_in_classes(tree):
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
                    f'"{filename}:{node.lineno}" Something went wrong. {vars(node)=}'
                ) from exc
            print(
                f"{filename}:{arg.lineno}:"
                f" Mixed positional and keyword arguments in function."
            )

    for node in yield_funcs_outside_classes(tree):
        if is_ignorable(node):
            continue
        if len(node.args.args) > num_allowed_args:
            violations += 1
            try:
                arg = node.args.args[0]
            except IndexError as exc:
                raise RuntimeError(
                    f'"{filename}:{node.lineno}" Something went wrong. {vars(node)=}'
                ) from exc
            print(
                f"{filename}:{arg.lineno}:"
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
