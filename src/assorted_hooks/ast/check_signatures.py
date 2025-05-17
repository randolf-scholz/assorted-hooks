#!/usr/bin/env python
r"""Checks for function signatures.

1. Checks that `positional` and `positional_or_keyword` arguments are not mixed.
2. Checks that `varargs` and `positional_or_keyword` arguments are not mixed.
3. Checks that not too many positional arguments are used in functions.
4. Checks that `__dunder__` methods use positional-only arguments.

Rationale:

1. Consider making `positional_or_keyword` arguments either `positional` or `keyword_only`.
2. Function signatures like `def foo(x, *args)` are not allowed because they prevent
   using the `positional_or_keyword` arguments as a keyword arguments.
   For instance, `foo(1, 2, 3 x=4)` would result in
   `TypeError: foo() got multiple values for argument 'x'`
3. Too many positional arguments in a function signature can lead to confusion and
   make the code less readable and maintainable.
"""

__all__ = [
    # Functions
    "is_fixable",
    "check_file",
    "main",
]

import argparse
import ast
import logging
import sys
from collections.abc import Collection
from copy import deepcopy
from functools import partial
from pathlib import Path

from assorted_hooks.ast.ast_utils import (
    Func,
    is_decorated_with,
    is_overload,
    is_staticmethod,
    replace_node,
    yield_functions_with_context,
)
from assorted_hooks.utils import is_dunder, is_private, run_checks

__logger__ = logging.getLogger(__name__)


def is_fixable(args: ast.arguments) -> bool:
    r"""Check if the function arguments can be fixed.

    We allow automatic fix if the function only uses positional arguments without defaults.
    """
    return not (args.defaults or args.kwarg or args.kwonlyargs)


def check_file(
    filepath: str | Path,
    /,
    *,
    fix: bool = False,
    max_args: int = 2,
    max_positional: int = 3,
    ignore_dunder: bool = False,
    ignore_names: Collection[str] = (),
    ignore_decorators: Collection[str] = (),
    ignore_overloads: bool = True,
    ignore_private: bool = False,
    ignore_wo_pos_only: bool = False,
) -> int:
    r"""Check whether functions contain POSITIONAL_OR_KEYWORD arguments."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    filename = str(path)
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=filename)
    fixable_dunders = []

    def is_ignorable(func: Func, /) -> bool:
        r"""Checks if the func can be ignored."""
        return (
            (ignore_wo_pos_only and not func.args.posonlyargs)
            or (ignore_dunder and is_dunder(func.name))
            or (ignore_overloads and is_overload(func))
            or (ignore_private and is_private(func.name))
            or (func.name in ignore_names)
            or any(is_decorated_with(func, name) for name in ignore_decorators)
        )

    for node, kind in yield_functions_with_context(tree):
        if is_ignorable(node):
            continue
        match kind:
            case "function":
                pk_args = node.args.args
                po_args = node.args.posonlyargs
            case "method":
                pk_args = (
                    node.args.args
                    if (is_staticmethod(node) or node.args.posonlyargs)
                    else node.args.args[1:]  # exclude self/cls
                )
                po_args = (
                    node.args.posonlyargs
                    if is_staticmethod(node)
                    else node.args.posonlyargs[1:]  # exclude self/cls
                )
            case _:
                raise TypeError(f"Unknown function kind: {kind!r}")

        if pk_args and (node.args.vararg is not None):
            violations += 1
            print(
                f"{filename}:{node.lineno}:"
                f" Mixed varargs and positional_or_keyword arguments in {kind!r}!"
            )
        if po_args and pk_args and (len(pk_args) > max_args):
            violations += 1
            print(
                f"{filename}:{node.lineno}:"
                f" Mixed positional and positional_or_keyword arguments in {kind!r}!"
            )
        if (len(po_args) + len(pk_args)) > max_positional:
            violations += 1
            print(
                f"{filename}:{node.lineno}: Too many positional arguments in {kind!r}!"
                f" (max {max_positional})"
            )
        if not ignore_dunder and is_dunder(node.name) and pk_args:
            violations += 1
            print(
                f"{filename}:{node.lineno}: Dunder method {node.name!r} should use"
                " positional-only arguments."
            )
            if is_fixable(node.args):
                fixable_dunders.append(node)

    if fix and fixable_dunders:
        lines = Path(filename).read_text().splitlines(keepends=True)
        for fn in sorted(
            fixable_dunders,
            key=lambda n: (n.lineno, n.col_offset),
            reverse=True,
        ):
            new_fn = deepcopy(fn)
            new_fn.args.posonlyargs = fn.args.posonlyargs + fn.args.args
            new_fn.args.args = []
            replace_node(lines, fn, new_fn)

        # write back
        with open(filename, "w", encoding="utf8") as f:
            f.writelines(lines)

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
        "-m",
        "--max-positional-args",
        action="store",
        type=int,
        default=3,
        help="Allow this many `positional_only + positional_or_keyword` arguments.",
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
        "--check-dunder-positional-only",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Check that dunder methods use positional-only arguments.",
    )
    parser.add_argument(
        "--fix",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Fix the violations.",
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

    checker = partial(
        check_file,
        fix=args.fix,
        max_args=args.max_args,
        max_positional=args.max_positional,
        ignore_dunder=args.ignore_dunder,
        ignore_names=args.ignore_names,
        ignore_overloads=args.ignore_overloads,
        ignore_wo_pos_only=args.ignore_without_positional_only,
        ignore_private=args.ignore_private,
        ignore_decorators=args.ignore_decorators,
    )
    run_checks(args.files, checker)


if __name__ == "__main__":
    main()
