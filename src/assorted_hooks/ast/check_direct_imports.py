#!/usr/bin/env python
r"""Check whether attributes in annotations shadow directly imported symbols.

Example:
    >>> import collections.abc as abc
    >>> from collections.abc import Sequence
    >>>
    >>> def foo(x: abc.Sequence) -> abc.Sequence:
    >>>     return x

    Would raise an error because `pd.DataFrame` shadows directly imported `DataFrame`.
"""

__all__ = [
    # functions
    "check_file",
    "check_direct_imports",
    "main",
]

import argparse
import ast
import logging
import sys
from pathlib import Path

from assorted_hooks.ast.ast_utils import get_imported_symbols, yield_imported_attributes
from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)


def check_direct_imports(tree: ast.AST, fname: str, /, *, debug: bool = False) -> int:
    violations = 0

    # find all violations
    for node, _, string in yield_imported_attributes(tree):
        violations += 1
        print(
            f"{fname}:{node.lineno}"
            f" use directly imported {node.attr!r} instead of {string!r}"
        )

    if violations and debug:
        imported_symbols = get_imported_symbols(tree)
        pad = " " * 4
        max_key_len = max(map(len, imported_symbols), default=0)
        print(pad, "Imported symbols:")
        for key, value in imported_symbols.items():
            print(2 * pad, f"{key:{max_key_len}} -> {value}")

    return violations


def check_file(filepath: str | Path, /, *, debug: bool = False) -> int:
    r"""Finds shadowed attributes in a file."""
    path = Path(filepath)
    filename = str(path)
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=filename)

    return check_direct_imports(tree, filename, debug=debug)


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
            violations += check_file(file, debug=args.debug)
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
