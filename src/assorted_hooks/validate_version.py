#!/usr/bin/env python
"""Validate version strings in pyproject.toml.

References:
    https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
"""

__all__ = [
    "VERSION_PATTERN",
    "VERSION_REGEX",
    "validate_version",
    "get_version_from_pyproject_toml",
    "main",
]


import argparse
import re

import tomllib

VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""

VERSION_REGEX = re.compile(
    r"^\s*" + VERSION_PATTERN + r"\s*$",
    re.VERBOSE | re.IGNORECASE,
)


def get_version_from_pyproject_toml() -> str:
    """Get the version from pyproject.toml."""
    with open("pyproject.toml", "rb") as f:
        toml = tomllib.load(f)

    version = NotImplemented

    if "project" in toml:
        version = toml["project"].get("version", NotImplemented)

    if version is NotImplemented and "tool" in toml and "poetry" in toml["tool"]:
        version = toml["tool"]["poetry"].get("version", NotImplemented)

    if version is NotImplemented:
        raise ValueError("Cannot find version in pyproject.toml.")

    return version


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


def main() -> None:
    """Main program."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    # find version
    version = get_version_from_pyproject_toml()
    validate_version(version, debug=args.debug)


if __name__ == "__main__":
    main()
