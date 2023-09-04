"""Checks that __all__ exists in modules."""

__all__ = [
    "check_file",
    "get__all__nodes",
    "is__all__node",
    "is_literal_list",
    "is_superfluous",
    "main",
]

import argparse
import ast
import logging
import sys
from ast import (
    AST,
    AnnAssign,
    Assign,
    AugAssign,
    Constant,
    Expr,
    Import,
    ImportFrom,
    Module,
    Name,
)
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import TypeGuard

from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)


def is_main(node: AST, /) -> bool:
    """Check whether node is `if __name__ == "__main__":` check."""
    return (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, Name)
        and node.test.left.id == "__name__"
        and len(node.test.ops) == 1
        and isinstance(node.test.ops[0], ast.Eq)
        and len(node.test.comparators) == 1
        and isinstance(node.test.comparators[0], Constant)
        and node.test.comparators[0].value == "__main__"
    )


def is__all__node(node: AST, /) -> TypeGuard[Assign | AnnAssign | AugAssign]:
    """Check whether a node is __all__."""
    if isinstance(node, Assign):
        targets = [target.id for target in node.targets if isinstance(target, Name)]
        has_all = "__all__" in targets
        if has_all and len(targets) > 1:
            raise ValueError("Multiple targets in __all__ assignment.")
        return has_all
    if isinstance(node, AnnAssign | AugAssign):
        return isinstance(node.target, Name) and node.target.id == "__all__"
    return False


def is_future_import(node: AST, /) -> bool:
    """Check whether a node is a future import."""
    if isinstance(node, ImportFrom):
        return node.module == "__future__"
    if isinstance(node, Import):
        return {imp.name for imp in node.names} <= {"__future__"}
    return False


def is_literal_list(node: AST, /) -> bool:
    """Check whether node is a literal list of strings."""
    return isinstance(node, ast.List) and all(
        isinstance(el, Constant) and isinstance(el.value, str) for el in node.elts
    )


def is_superfluous(tree: Module, /) -> bool:
    """Check whether __all__ is superfluous."""
    # Basically, superfluous is the case if the file
    # only contains statements and expressions that do not produce locals.
    # currently this function just checks if there is only a single assignment
    # and the rest of statements are Expr.
    body = list(tree.body)  # make a copy

    # ignore __main__ code if present
    for node in tree.body:
        if is_main(node):
            # remove from copy
            body.remove(node)

    # ignore first __all__ if present
    for node in tree.body:
        if is__all__node(node):
            body.remove(node)
            break  # only remove the first occurrence

    node_types = Counter(type(node) for node in body)
    return set(node_types) <= {Expr, ast.Pass}


def is_at_top(node: Assign | AnnAssign, /, *, module: Module) -> bool:
    """Check whether node is at the top of the module.

    The only things allowed before __all__ are:
        - module docstring
        - __future__ imports
    """
    body = module.body
    loc = body.index(node)

    # exclude docstring
    assert len(body) > 0, "Expected at least one node in the body."
    start = isinstance(body[0], Expr)

    for n in body[start:loc]:
        if not is_future_import(n):
            return False
    return True


def get_duplicate_keys(node: Assign | AnnAssign | AugAssign, /) -> set[str]:
    """Check if __all__ node has duplicate keys."""
    assert node.value is not None, "Expected __all__ to have a value."
    assert is_literal_list(node.value), "Expected literal list."
    elements = Counter(el.value for el in node.value.elts)  # type: ignore[attr-defined]
    return {key for key, count in elements.items() if count > 1}


def get__all__nodes(tree: Module, /) -> Iterator[Assign | AnnAssign | AugAssign]:
    """Get the __all__ node from the tree."""
    # NOTE: we are only interested in the module body.
    for node in tree.body:
        if is__all__node(node):
            yield node


def check_file(
    fname: str | Path,
    /,
    *,
    allow_missing: bool = True,
    warn_non_literal: bool = True,
    warn_annotated: bool = True,
    warn_duplicate_keys: bool = True,
    warn_location: bool = True,
    warn_multiple_definitions: bool = True,
    warn_superfluous: bool = True,
) -> bool:
    """Check a single file."""
    with open(fname, "rb") as file:
        tree = ast.parse(file.read())

    if not isinstance(tree, Module):
        raise ValueError(f"Expected ast.Module, got {type(tree)}")

    passed = True
    node_list: list[Assign | AnnAssign | AugAssign] = []

    match tree.body:
        case [] | [Expr()]:
            if allow_missing:
                return True
        case _:
            node_list.extend(get__all__nodes(tree))

    match node_list:
        case []:
            if not is_superfluous(tree):
                passed = False
                print(f"{fname!s}:0: No __all__ found.")
        case [node, *nodes]:
            if not isinstance(node, Assign | AnnAssign):
                raise TypeError("Expected __all__ to be an assignment.")
            if node.value is None:
                raise ValueError("Expected __all__ to have a value.")
            if warn_non_literal and not is_literal_list(node.value):
                passed = False
                print(f"{fname!s}:{node.lineno}: __all__ is not a literal list.")
            if warn_annotated and isinstance(node, AnnAssign):
                passed = False
                print(f"{fname!s}:{node.lineno}: __all__ is annotated.")
            if warn_multiple_definitions and nodes:
                passed = False
                print(f"{fname!s}:{node.lineno}: Multiple __all__ found.")
                for n in nodes:
                    print(f"{fname!s}:{n.lineno}: additional __all__.")
            if warn_superfluous and is_superfluous(tree):
                passed = False
                print(f"{fname!s}:{node.lineno}: __all__ is superfluous.")
            if warn_location and not is_at_top(node, module=tree):
                passed = False
                print(f"{fname!s}:{node.lineno}: __all__ is not at the top.")
            if warn_duplicate_keys and (keys := get_duplicate_keys(node)):
                passed = False
                print(f"{fname!s}:{node.lineno}: __all__ has duplicate {keys=}.")

    return passed


def main():
    """Main program."""
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
        "--warn-non-literal",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Check that __all__ is a literal list of strings.",
    )
    parser.add_argument(
        "--allow-missing",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Don't raise an error if file has no content than a module docstring.",
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
        default=True,
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
    passed = True
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            passed &= check_file(
                file,
                allow_missing=args.allow_missing,
                warn_annotated=args.warn_annotated,
                warn_duplicate_keys=args.warn_duplicate_keys,
                warn_location=args.warn_location,
                warn_multiple_definitions=args.warn_multiple_definitions,
                warn_non_literal=args.warn_non_literal,
                warn_superfluous=args.warn_superfluous,
            )
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
