#!/usr/bin/env python
r"""Validate version strings in pyproject.toml.

References:
    - https://peps.python.org/pep-0440
"""

__all__ = [
    # Functions
    "check_file",
    "main",
]

import argparse
import tomllib
from itertools import chain

from packaging.requirements import InvalidRequirement, Requirement

from assorted_hooks.utils import yield_deps, yield_dev_deps


def check_file(fname: str, /, *, debug: bool = False) -> int:
    r"""Get the version from pyproject.toml."""
    with open(fname, "rb") as file:
        pyproject = tomllib.load(file)

    violations = 0

    requirements: set[Requirement] = set()

    for dep in chain(yield_deps(pyproject), yield_dev_deps(pyproject)):
        try:
            req = Requirement(dep)
        except InvalidRequirement:
            print(f"Invalid requirement: {dep!r}")
            violations += 1
            continue
        else:
            requirements.add(req)

    if debug:
        print(f"Found {len(requirements)} requirements.")
        for req in sorted(requirements, key=lambda x: x.name):
            print(f"  {req}")

    return violations


def main() -> None:
    r"""Main program."""
    parser = argparse.ArgumentParser(
        description="Validate version strings in pyproject.toml.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # optional single argument specifying the pyproject.toml file
    parser.add_argument(
        "pyproject_file",
        nargs="?",
        default="pyproject.toml",
        type=str,
        help="The path to the pyproject.toml file.",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Print debug information.",
    )
    args = parser.parse_args()

    # run script
    try:
        violations = check_file(args.pyproject_file, debug=args.debug)
    except Exception as exc:
        raise RuntimeError(f'Checking file "{args.pyproject_file!s}" failed!') from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
