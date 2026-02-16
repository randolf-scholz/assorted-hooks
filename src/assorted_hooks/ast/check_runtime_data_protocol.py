#!/usr/bin/env python
r"""Checks that data-Protocols are not used with `@runtime_checkable`."""

__all__ = [
    "is_runtime_data_protocol",
    "check_runtime_data_protocol",
    "check_file",
    "main",
]

import argparse
import ast
import logging
import sys
from ast import AST, AnnAssign, ClassDef, Name
from pathlib import Path

from typing_extensions import TypeIs

from assorted_hooks.utils import get_path_relative_to_git_root, get_python_files

__logger__ = logging.getLogger(__name__)


def is_runtime_data_protocol(node: AST) -> TypeIs[ClassDef]:
    r"""Checks if a node is a class with the @runtime_checkable decorator."""
    match node:
        case ClassDef(decorator_list=decorator_list):
            # check that the class has the @runtime_checkable decorator
            for decorator in decorator_list:
                if isinstance(decorator, Name) and decorator.id == "runtime_checkable":
                    break
            else:
                return False
            # check that the class is a Protocol
            for base in node.bases:
                if isinstance(base, Name) and base.id == "Protocol":
                    break
            else:
                return False
            # check that the protocol is a data protocol, i.e. has an annotated attribute
            return any(isinstance(body, AnnAssign) for body in node.body)
        # non class node
        case _:
            return False


def check_runtime_data_protocol(tree: AST, fname: str = "", /) -> int:
    violations = 0

    # find all violations
    for node in ast.walk(tree):
        if is_runtime_data_protocol(node):
            violations += 1
            print(
                f"{fname}:{node.lineno}: "
                "Do not use @runtime_checkable with data-protocols!"
            )

    return violations


def check_file(filepath: str | Path, /, *, debug: bool = False) -> int:
    r"""Finds shadowed attributes in a file."""
    path = Path(filepath)
    filename = str(get_path_relative_to_git_root(path))

    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=filename)

    if debug:
        __logger__.debug("checking file %s", filename)
    return check_runtime_data_protocol(tree, filename)


def main() -> None:
    r"""Main function."""
    parser = argparse.ArgumentParser(
        description="Checks that Bar is used instead of foo.Bar if both foo and Bar are imported.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
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
            violations += check_file(file, debug=args.debug)
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
