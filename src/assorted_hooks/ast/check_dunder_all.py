r"""Checks that __all__ exists in modules."""

__all__ = [
    "check_file",
    "get_duplicate_keys",
    "is_at_top",
    "is_superfluous",
    "main",
]

import argparse
import ast
import logging
import sys
from ast import (
    AnnAssign,
    Assign,
    AugAssign,
    Expr,
    Module,
    Pass,
)
from collections import Counter
from pathlib import Path

from assorted_hooks.ast.ast_utils import (
    is_dunder_all,
    is_dunder_main,
    is_future_import,
    is_literal_list,
    yield_dunder_all,
)
from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)


def is_superfluous(tree: Module, /) -> bool:
    r"""Check whether __all__ is superfluous."""
    # Basically, superfluous is the case if the file
    # only contains statements and expressions that do not produce locals.
    # currently this function just checks if there is only a single assignment
    # and the rest of statements are Expr.
    body = list(tree.body)  # make a copy

    # ignore __main__ code if present
    for node in tree.body:
        if is_dunder_main(node):
            # remove from copy
            body.remove(node)

    # ignore first __all__ if present
    for node in tree.body:
        if is_dunder_all(node):
            body.remove(node)
            break  # only remove the first occurrence

    node_types = Counter(type(node) for node in body)
    return set(node_types) <= {Expr, Pass}


def is_at_top(node: Assign | AnnAssign, /, *, module: Module) -> bool:
    r"""Check whether node is at the top of the module.

    The only things allowed before __all__ are:
        - module docstring
        - __future__ imports
    """
    body = module.body
    loc = body.index(node)

    # exclude docstring
    if len(body) <= 0:
        raise ValueError("Expected at least one node in the body.")

    start = isinstance(body[0], Expr)
    return all(is_future_import(_node) for _node in body[start:loc])


def get_duplicate_keys(node: Assign | AnnAssign | AugAssign, /) -> set[str]:
    r"""Check if __all__ node has duplicate keys."""
    if node.value is None:
        raise ValueError("Expected __all__ to have a value.")
    if not is_literal_list(node.value):
        raise ValueError(f"Expected literal list, got {type(node.value)}.")

    elements = Counter(el.value for el in node.value.elts)  # type: ignore[attr-defined]
    return {key for key, count in elements.items() if count > 1}


def check_file(
    filepath: str | Path,
    /,
    *,
    warn_annotated: bool = True,
    warn_duplicate_keys: bool = True,
    warn_location: bool = True,
    warn_missing: bool = True,
    allow_missing_empty: bool = True,
    warn_multiple_definitions: bool = True,
    warn_non_literal: bool = True,
    warn_superfluous: bool = True,
) -> int:
    r"""Check a single file."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    fname = str(path)
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=fname)

    if not isinstance(tree, Module):
        raise TypeError(f"Expected ast.Module, got {type(tree)}")

    node_list: list[Assign | AnnAssign | AugAssign] = []

    match tree.body:
        case [] | [Expr()]:
            if allow_missing_empty:
                return 0
        case _:
            node_list.extend(yield_dunder_all(tree))

    match node_list:
        case []:
            if warn_missing and not is_superfluous(tree):
                violations += 1
                print(f"{fname}:0: No __all__ found.")
        case [node, *nodes]:
            if not isinstance(node, Assign | AnnAssign):
                raise TypeError("Expected __all__ to be an assignment.")
            if node.value is None:
                raise ValueError("Expected __all__ to have a value.")
            if warn_non_literal and not is_literal_list(node.value):
                violations += 1
                print(f"{fname}:{node.lineno}: __all__ is not a literal list.")
            if warn_annotated and isinstance(node, AnnAssign):
                violations += 1
                print(f"{fname}:{node.lineno}: __all__ is annotated.")
            if warn_multiple_definitions and nodes:
                violations += 1
                print(f"{fname}:{node.lineno}: Multiple __all__ found.")
                for n in nodes:
                    print(f"{fname}:{n.lineno}: additional __all__.")
            if warn_superfluous and is_superfluous(tree):
                violations += 1
                print(f"{fname}:{node.lineno}: __all__ is superfluous.")
            if warn_location and not is_at_top(node, module=tree):
                violations += 1
                print(f"{fname}:{node.lineno}: __all__ is not at the top.")
            if warn_duplicate_keys and (keys := get_duplicate_keys(node)):
                violations += 1
                print(f"{fname}:{node.lineno}: __all__ has duplicate {keys=}.")

    return violations


def main():
    r"""Main program."""
    parser = argparse.ArgumentParser(
        description="Check that __all__ exists.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument(
        "--warn-missing",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Warn if __all__ is missing.",
    )
    parser.add_argument(
        "--allow-missing-empty",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Allow missing __all__ if files is essentially empty.",
    )
    parser.add_argument(
        "--warn-non-literal",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Check that __all__ is a literal list of strings.",
    )
    parser.add_argument(
        "--warn-annotated",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Warn if __all__ is annotated.",
    )
    parser.add_argument(
        "--warn-location",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Warn if __all__ is not at the top of the file.",
    )
    parser.add_argument(
        "--warn-superfluous",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Warn if __all__ is superfluous.",
    )
    parser.add_argument(
        "--warn-multiple-definitions",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Warn if multiple __all__ definitions are present.",
    )
    parser.add_argument(
        "--warn-duplicate-keys",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Warn if __all__ contains the same key twice.",
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
                allow_missing_empty=args.allow_missing_empty,
                warn_annotated=args.warn_annotated,
                warn_duplicate_keys=args.warn_duplicate_keys,
                warn_location=args.warn_location,
                warn_missing=args.warn_missing,
                warn_multiple_definitions=args.warn_multiple_definitions,
                warn_non_literal=args.warn_non_literal,
                warn_superfluous=args.warn_superfluous,
            )
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
