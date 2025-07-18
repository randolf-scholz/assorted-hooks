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
    "check_file",
    "fix_dunder_positional_only",
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
    patch_node,
    yield_functions_and_context,
)
from assorted_hooks.utils import is_dunder, is_private, run_checks

__logger__ = logging.getLogger(__name__)

_DUNDER_BLACKLIST: frozenset[str] = frozenset({
    "__init__",
    "__new__",
    "__call__",
    "__post_init__",
})
r"""Dunder methods that should not be fixed."""


def fix_dunder_positional_only(lines: list[str], nodes: list[Func], /) -> list[str]:
    patched_lines = deepcopy(lines)

    for fn in sorted(
        nodes,
        key=lambda n: (n.lineno, n.col_offset),
        reverse=True,
    ):
        new_fn = deepcopy(fn)
        num = len(fn.args.args) - len(fn.args.defaults)
        new_fn.args.posonlyargs = fn.args.posonlyargs + fn.args.args[:num]
        new_fn.args.args = fn.args.args[num:]
        patched_lines = patch_node(patched_lines, fn.args, new_fn.args)
    return patched_lines


def check_file(
    filepath: str | Path,
    /,
    *,
    allow_mixed_args: bool = True,
    fix: bool = False,
    max_args: int = 2,
    max_positional_args: int = 3,
    ignore_dunder: bool = False,
    ignore_names: Collection[str] = (),
    ignore_decorators: Collection[str] = (),
    ignore_overloads: bool = True,
    ignore_private: bool = False,
) -> int:
    r"""Check whether functions contain POSITIONAL_OR_KEYWORD arguments."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    # get file name relative to the current working directory
    filename = str(
        path if not path.is_relative_to(Path.cwd()) else path.relative_to(Path.cwd())
    )

    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=filename)
    fixable_dunders = []

    def is_ignorable(func: Func, /) -> bool:
        r"""Checks if the func can be ignored."""
        return (
            any(is_decorated_with(func, name) for name in ignore_decorators)
            or (ignore_dunder and is_dunder(func.name))
            or (ignore_overloads and is_overload(func))
            or (ignore_private and is_private(func.name))
            or (func.name in ignore_names)
        )

    for fn_ctx in yield_functions_and_context(tree):
        node = fn_ctx.node
        kind = fn_ctx.kind
        fn_repr = f"{kind.value} {node.name!r}"
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
                raise TypeError(f"Unknown function kind: {fn_repr}")

        if pk_args and (node.args.vararg is not None):
            violations += 1
            print(
                f"{filename}:{node.lineno}:"
                f" Mixed varargs and positional_or_keyword arguments in {fn_repr}"
            )
        if pk_args and po_args and not allow_mixed_args:
            violations += 1
            print(
                f"{filename}:{node.lineno}:"
                f" Mixed positional_only and positional_or_keyword arguments in {fn_repr}"
            )
        if len(pk_args) > max_args:
            violations += 1
            print(
                f"{filename}:{node.lineno}: Too many positional_or_keyword arguments in {fn_repr}"
                f" (max {max_args})"
            )
        if (len(po_args) + len(pk_args)) > max_positional_args:
            violations += 1
            print(
                f"{filename}:{node.lineno}: Too many positional arguments in {fn_repr}"
                f" (max {max_positional_args})"
            )
        if (
            not ignore_dunder
            and is_dunder(node.name)
            # exclude signatures with only self/cls and no other arguments
            and (len(pk_args) > 1 or (pk_args and po_args))
            and node.name not in _DUNDER_BLACKLIST
        ):
            violations += 1
            print(
                f"{filename}:{node.lineno}: Dunder method {node.name!r} should use"
                " positional-only arguments."
            )
            fixable_dunders.append(node)

    if fix and fixable_dunders:
        original = Path(filename).read_text().splitlines(keepends=True)
        new_lines = fix_dunder_positional_only(original, fixable_dunders)
        # write back
        with open(filename, "w", encoding="utf8") as f:
            f.writelines(new_lines)

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
        "--max-args",
        action="store",
        type=int,
        default=2,
        help="Allow this many positional_or_keyword arguments.",
    )
    parser.add_argument(
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
        "--ignore-overloads",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Ignore FunctionDefs that are @overload decorated.",
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
        help="Check that dunder methods use positional-only arguments (excludes init and call) .",
    )
    parser.add_argument(
        "--allow-mixed-args",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Allow the same signature to include both positional_only and positional_or_keyword arguments.",
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
        allow_mixed_args=args.allow_mixed_args,
        max_args=args.max_positional_args,
        max_positional_args=args.max_positional_args,
        ignore_dunder=args.ignore_dunder,
        ignore_names=args.ignore_names,
        ignore_overloads=args.ignore_overloads,
        ignore_private=args.ignore_private,
        ignore_decorators=args.ignore_decorators,
    )
    run_checks(args.files, checker)


if __name__ == "__main__":
    main()
