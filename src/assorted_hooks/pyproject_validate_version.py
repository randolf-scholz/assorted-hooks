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
    "VERSION_REGEX",
    # Functions
    "validate_version",
    "process_pyproject",
    "main",
]


import argparse
import re
import tomllib

# https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
VERSION = r"""(?ix:                                       # case-insensitive, verbose
    v?(?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_.]?
            (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
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
VERSION_GROUP = rf"""(?P<version>{VERSION})"""
VERSION_REGEX: re.Pattern = re.compile(VERSION_GROUP)


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


def validate_version(version: str, /, *, debug: bool = False) -> None:
    """Validate a version string."""
    match = VERSION_REGEX.match(version)

    if match is None:
        raise ValueError(f"Invalid version string: {version!r}.")

    if debug:
        groups = {k: v for k, v in match.groupdict().items() if v is not None}
        print(f"Version {version}, consisting of {groups=}")

    groups = match.groupdict()
    if groups["epoch"] is not None and groups["release"] is None:
        raise ValueError(f"Invalid version string: {version!r}.")


def process_pyproject(fname: str, /, *, debug: bool = False) -> None:
    """Get the version from pyproject.toml."""
    with open(fname, "rb") as file:
        toml = tomllib.load(file)

    version = get_version(toml)
    validate_version(version, debug=debug)


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
        action="store_true",
        help="Print debug information.",
    )
    args = parser.parse_args()

    # run script
    process_pyproject(args.pyproject_file, debug=args.debug)


if __name__ == "__main__":
    main()
