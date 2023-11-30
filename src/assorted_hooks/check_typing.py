#!/usr/bin/env python
"""Disallow mixed positional and keyword arguments in function-defs."""

__all__ = [
    "check_pep604_union",
    "check_no_return_union",
    "check_overload_default_ellipsis",
    "check_no_optional",
    "check_no_future_annotations",
    "check_optional",
    "check_file",
    "main",
]
import argparse
import ast
import builtins
import logging
import sys
from ast import (
    AST,
    AsyncFunctionDef,
    BinOp,
    BitOr,
    Constant,
    FunctionDef,
    ImportFrom,
    Name,
    Subscript,
)
from collections.abc import Iterator
from pathlib import Path
from typing import TypeAlias, TypeGuard

from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)

Func: TypeAlias = FunctionDef | AsyncFunctionDef
"""Type alias for function-defs."""


def is_typing_union(node: AST, /) -> bool:
    """True if the return node is a union."""
    match node:
        case Subscript(value=Name(id="Union")):
            return True
        case _:
            return False


def is_union(node: AST, /) -> bool:
    """True if the return node is a union."""
    match node:
        case Subscript(value=Name(id="Union")):
            return True
        case BinOp(op=BitOr()):
            return True
        case _:
            return False


def is_function_def(node: AST, /) -> TypeGuard[Func]:
    """True if the return node is a function definition."""
    return isinstance(node, Func)  # type: ignore[misc, arg-type]


def has_union(tree: AST, /) -> bool:
    """True if the return node is a union."""
    for node in ast.walk(tree):
        if is_union(node):
            return True
    return False


def get_function_defs(tree: AST, /) -> Iterator[Func]:
    """Get all return nodes."""
    for node in ast.walk(tree):
        if is_function_def(node):
            yield node


def get_overloads(tree: AST, /) -> Iterator[Func]:
    """Get all function definitions that are decorated with `@overload`."""
    for node in ast.walk(tree):
        match node:
            case FunctionDef(decorator_list=[Name(id="overload"), *_]):
                yield node
            case AsyncFunctionDef(decorator_list=[Name(id="overload"), *_]):
                yield node


def check_no_future_annotations(tree: AST, /, *, fname: str) -> int:
    """Make sure PEP563 is not used."""
    violations = 0
    for node in ast.walk(tree):
        match node:
            # FIXME: https://github.com/python/cpython/issues/107497
            case ImportFrom(module="__future__") as future_import:
                for alias in future_import.names:
                    if alias.name == "annotations":
                        violations += 1
                        print(f"{fname!s}:{node.lineno}: Do not use PEP563!")
    return violations


def check_overload_default_ellipsis(tree: AST, /, *, fname: str) -> int:
    """Check that keyword arguments in overloads assign Ellipsis instead of a value."""
    violations = 0

    for node in get_overloads(tree):
        pos_defaults = node.args.defaults
        pos_args = node.args.posonlyargs + node.args.args
        pos_args = pos_args[-len(pos_defaults) :] if pos_defaults else []
        for arg, default in zip(pos_args, pos_defaults, strict=True):
            match default:
                case None | Constant(value=builtins.Ellipsis):
                    continue
                case _:
                    violations += 1
                    print(
                        f"{fname!s}:{node.lineno}: Default value for"
                        f" {arg.arg!r} inside @overload should be '...'"
                    )

        kw_args = [] if node.args.kwonlyargs is None else node.args.kwonlyargs
        kw_defaults = [] if node.args.kw_defaults is None else node.args.kw_defaults

        for kwarg, kw_default in zip(kw_args, kw_defaults, strict=True):
            match kw_default:
                case None | Constant(value=builtins.Ellipsis):
                    continue
                case _:
                    violations += 1
                    print(
                        f"{fname!s}:{node.lineno}: Default value for"
                        f" {kwarg.arg!r} inside @overload should be '...'"
                    )
    return violations


def check_pep604_union(tree: AST, /, *, fname: str) -> int:
    """Check that X | Y is used instead of Union[X, Y]."""
    # FIXME: https://github.com/python/mypy/issues/11673
    violations = 0

    for node in ast.walk(tree):
        if is_typing_union(node):
            violations += 1
            print(f"{fname!s}:{node.lineno}: Use X | Y instead of Union[X, Y]!")

    return violations


def check_no_return_union(tree: AST, /, *, recursive: bool, fname: str) -> int:
    """Check if function returns a union type."""
    # FIXME: https://github.com/python/mypy/issues/11673
    violations = 0

    for node in get_function_defs(tree):
        if node.returns is None:
            continue
        if is_union(node.returns):
            violations += 1
            print(f"{fname!s}:{node.lineno}: Do not return union type!")
        elif recursive and has_union(node.returns):
            violations += 1
            print(f"{fname!s}:{node.lineno}: Do not return union type!")

    return violations


def check_no_optional(tree: AST, /, *, fname: str) -> int:
    """Check that `None | T` is used instead of `Optional[T]`."""
    violations = 0

    for node in ast.walk(tree):
        match node:
            case Subscript(value=Name(id="Optional")):
                violations += 1
                print(f"{fname!s}:{node.lineno}: Use None | X instead of Optional[X]")

    return violations


def check_optional(tree: AST, /, *, fname: str) -> int:
    """Check that `Optional[T]` is used instead of `None | T`."""
    violations = 0

    for node in ast.walk(tree):
        match node:
            case BinOp(op=BitOr(), left=Constant(value=None)):
                violations += 1
                print(f"{fname!s}:{node.lineno}: Use Optional[X] instead of None | X")
            case BinOp(op=BitOr(), right=Constant(value=None)):
                violations += 1
                print(f"{fname!s}:{node.lineno}: Use Optional[X] instead of X | None")

    return violations


def check_file(file_or_path: str | Path, /, *, options: argparse.Namespace) -> int:
    """Check whether the file contains mixed positional and keyword arguments."""
    fname = str(file_or_path)
    with open(file_or_path, "rb") as file:
        tree = ast.parse(file.read(), filename=fname)

    violations = 0

    if options.check_optional:
        violations += check_optional(tree, fname=fname)
    if options.check_no_optional:
        violations += check_no_optional(tree, fname=fname)
    if options.check_pep604_union:
        violations += check_pep604_union(tree, fname=fname)
    if options.check_overload_default_ellipsis:
        violations += check_overload_default_ellipsis(tree, fname=fname)
    if options.check_no_future_annotations:
        violations += check_no_future_annotations(tree, fname=fname)
    if options.check_no_return_union:
        violations += check_no_return_union(
            tree, recursive=options.check_no_return_union_recursive, fname=fname
        )
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
        "--check-no-optional",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that Optional is not used.",
    )
    parser.add_argument(
        "--check-optional",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that Optional is used.",
    )
    parser.add_argument(
        "--check-pep604-union",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that PEP604 unions are used.",
    )
    parser.add_argument(
        "--check-overload-default-ellipsis",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Recursively check for unions.",
    )
    parser.add_argument(
        "--check-no-return-union",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that function does not return Union.",
    )
    parser.add_argument(
        "--check-no-return-union-recursive",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Recursively check for unions.",
    )
    parser.add_argument(
        "--check-no-future-annotations",
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
            violations += check_file(file, options=args)
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-'*79}\nFound {violations} violations.")
        sys.exit(1)
