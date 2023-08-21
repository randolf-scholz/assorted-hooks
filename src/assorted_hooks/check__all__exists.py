"""Checks that __all__ exists in modules."""

__all__ = [
    "all_superfluous",
    "check_file",
    "get__all__nodes",
    "main",
]

import argparse
import ast
import sys
from ast import AST, AnnAssign, Assign, AugAssign, Constant, Expr, List, Module, Name
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import TypeGuard

from assorted_hooks.utils import get_python_files


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


def get__all__nodes(tree: Module, /) -> Iterator[Assign | AnnAssign | AugAssign]:
    """Get the __all__ node from the tree."""
    # NOTE: we are only interested in the module body.
    for node in tree.body:
        if is__all__node(node):
            yield node


def all_superfluous(tree: Module, /) -> bool:
    """Check whether __all__ is superfluous."""
    # Basically, superfluous is the case if the file
    # only contains statements and expressions that do not produce locals.
    # currently this function just checks if there is only a single assignment
    # and the rest of statements are Expr.
    node_types = Counter(type(node) for node in tree.body)
    return (
        set(node_types) <= {Expr, Assign, AnnAssign}
        and node_types.get(Assign, 0) + node_types.get(AnnAssign, 0) == 1
    )


def is_literal_list(node: Assign | AnnAssign, /) -> bool:
    if not isinstance(node.value, List):
        return False
    return all(
        isinstance(el, Constant) and isinstance(el.value, str) for el in node.value.elts
    )


def check_file(
    fname: str | Path,
    /,
    *,
    allow_missing: bool = True,
    assert_literal: bool = True,
    warn_annotated: bool = True,
    warn_location: bool = True,
    warn_multiple: bool = True,
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
            print(f'"{fname!s}:0" No __all__ found.')
            passed = False
        case [node, *nodes]:
            assert isinstance(
                node, Assign | AnnAssign
            ), "Expected __all__ to be an assignment."
            if assert_literal and not is_literal_list(node):
                passed = False
                print(f'"{fname!s}:{node.lineno}" __all__ is not a literal list.')
            if warn_annotated and isinstance(node, AnnAssign):
                passed = False
                print(f'"{fname!s}:{node.lineno}" __all__ is annotated.')
            if nodes and warn_multiple:
                passed = False
                print(f'"{fname!s}:{node.lineno}" Multiple __all__ found.')
                for n in nodes:
                    print(f'"{fname!s}:{n.lineno}" additional __all__.')
            if warn_superfluous and all_superfluous(tree):
                passed = False
                print(f'"{fname!s}:{node.lineno}" __all__ is superfluous.')
            if warn_location and node not in tree.body[:2]:
                passed = False
                print(f'"{fname!s}:{node.lineno}" __all__ is not at the top.')

    return passed


def main():
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
        "--assert-literal",
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
        "--warn-multiple",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Warn if multiple __all__ are present.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information.",
    )
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
            allow_missing=args.allow_missing,
            assert_literal=args.assert_literal,
            warn_annotated=args.warn_annotated,
            warn_location=args.warn_location,
            warn_multiple=args.warn_multiple,
            warn_superfluous=args.warn_superfluous,
        )

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
