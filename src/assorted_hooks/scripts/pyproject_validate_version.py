#!/usr/bin/env python
"""Validate version strings in pyproject.toml.

References
----------
- https://peps.python.org/pep-0440
"""

__all__ = [
    # CONSTANTS
    "VERSION",
    "VERSION_GROUP",
    "RE_VERSION_GROUP",
    "RE_VERSION",
    # Functions
    "get_version",
    "validate_version",
    "check_file",
    "main",
]

import argparse
import importlib
import re
import sys

# import toml library
for name in ("tomllib", "tomlkit", "tomli"):
    try:
        tomllib = importlib.import_module(name)
        break
    except ImportError:
        pass
else:
    raise ImportError(
        "This pre-commit hook runs in the local interpreter and requires a suitable TOML-library!"
        " Please use python≥3.11 or install one of 'tomlkit' or 'tomli'."
    )


def ignore_subgroups(pattern: str | re.Pattern, /) -> str:
    """Ignore all named groups in the given pattern."""
    pattern = pattern if isinstance(pattern, str) else pattern.pattern
    return re.sub(r"\(\?P<[^>]+>", r"(?:", pattern)


# https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
RE_VERSION = re.compile(
    r"""(?ix:                                       # case-insensitive, verbose
        v?(?:
            (?:(?P<epoch>[0-9]+)!)?                           # epoch
            (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
            (?P<pre>                                          # pre-release
                [-_.]?
                (?P<pre_l>(?:a|b|c|rc|alpha|beta|pre|preview))
                [-_.]?
                (?P<pre_n>[0-9]+)?
            )?
            (?P<post>                                         # post release
                (?:-(?P<post_n1>[0-9]+))
                |
                (?:
                    [-_.]?
                    (?P<post_l>post|rev|r)
                    [-_.]?
                    (?P<post_n2>[0-9]+)?
                )
            )?
            (?P<dev>                                          # dev release
                [-_.]?
                (?P<dev_l>dev)
                [-_.]?
                (?P<dev_n>[0-9]+)?
            )?
        )
        (?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?        # local version
    )"""
)
VERSION = RE_VERSION.pattern
RE_VERSION_GROUP = re.compile(rf"""(?P<version>{VERSION})""")
VERSION_GROUP = RE_VERSION_GROUP.pattern
assert "version" in RE_VERSION_GROUP.groupindex, f"{RE_VERSION_GROUP.groupindex=}."


def get_version(pyproject: dict, /) -> str:
    """Get the version from pyproject.toml."""
    try:
        project_version = pyproject["project"]["version"]
    except KeyError:
        project_version = None

    try:
        poetry_version = pyproject["tool"]["poetry"]["version"]
    except KeyError:
        poetry_version = None

    match project_version, poetry_version:
        case None, None:
            raise ValueError("Cannot find version in pyproject.toml.")
        case str(), None:
            return project_version
        case None, str():
            return poetry_version
        case str(), str():
            if project_version != poetry_version:
                raise ValueError(
                    "Version in pyproject.toml is ambiguous!"
                    f" Found project.version={project_version!r}"
                    f" and tool.poetry.version={poetry_version!r}."
                )
            return project_version
        case _:
            raise TypeError("Unexpected types, expected str.")


def validate_version(version: str, /, *, debug: bool = False) -> bool:
    """Validate a version string."""
    passed = True
    match = RE_VERSION_GROUP.match(version)

    if match is None:
        print(f"Invalid version string: {version!r}.")
        return False

    groups = match.groupdict()

    if debug:
        print(f"Version {version}, consisting of {groups=}")

    if groups["epoch"] is not None and groups["release"] is None:
        passed = False
        print(f"Invalid version string: {version!r}.")

    return passed


def check_file(fname: str, /, *, debug: bool = False) -> bool:
    """Get the version from pyproject.toml."""
    with open(fname, "rb") as file:
        toml = tomllib.load(file)

    # get version
    version = get_version(toml)

    return validate_version(version, debug=debug)


def main() -> None:
    """Main program."""
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
        type=bool,
        default=False,
        help="Print debug information.",
    )
    args = parser.parse_args()

    # run script
    try:
        passed = check_file(args.pyproject_file, debug=args.debug)
    except Exception as exc:
        raise RuntimeError(f'Checking file "{args.pyproject_file!s}" failed!') from exc

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
