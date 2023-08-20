#!/usr/bin/env python
"""Updates the pyproject.toml dependencies to the currently installed versions.

References
----------
- (Final) PEP 440 – Version Identification and Dependency Specification
  https://peps.python.org/pep-0440/
- (Final) PEP 508 – Dependency specification for Python Software Packages
  https://peps.python.org/pep-0508/
- (Final) PEP 621 – Storing project metadata in pyproject.toml
  https://peps.python.org/pep-0621/
- (Superseded) PEP 631 – Dependency specification in pyproject.toml based on PEP 508
  https://peps.python.org/pep-0631/
- (Rejected) PEP 633 – Dependency specification in pyproject.toml using an exploded TOML table
  https://peps.python.org/pep-0633/
"""


__all__ = [
    # CONSTANTS
    "EXTRAS",
    "EXTRAS_GROUP",
    "EXTRAS_REGEX",
    "NAME",
    "NAME_GROUP",
    "NAME_REGEX",
    "POETRY_DEP",
    "POETRY_DEP_GROUP",
    "POETRY_DEP_REGEX",
    "POETRY_EXT_DEP",
    "POETRY_EXT_DEP_GROUP",
    "POETRY_EXT_DEP_REGEX",
    "PROJECT_DEP",
    "PROJECT_DEP_GROUP",
    "PROJECT_DEP_REGEX",
    "VERSION",
    "VERSION_GROUP",
    "VERSION_REGEX",
    # Functions
    "get_pip_package_dict",
    "main",
    "pyproject_update_dependencies",
    "strip_version",
    "update_versions",
]

import argparse
import json
import re
import subprocess
from functools import cache
from typing import Literal


def ignore_subgroups(pattern: str, /) -> str:
    """Ignore all named groups in the given pattern."""
    return re.sub(r"\(\?P<[^>]+>", r"(?:", pattern)


# https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
VERSION = r"""(?ix:                                       # case-insensitive, verbose
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
VERSION_GROUP = rf"""(?P<version>{ignore_subgroups(VERSION)})"""
VERSION_REGEX: re.Pattern = re.compile(VERSION_GROUP)
assert VERSION_REGEX.groups == 1, f"{VERSION_REGEX.groups=}."

# https://peps.python.org/pep-0508/#names
# NOTE: we modify this regex a bit to allow to match inside context
NAME = r"""\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?\b"""
NAME_GROUP = rf"""(?P<name>{NAME})"""
NAME_REGEX = re.compile(NAME_GROUP)
assert VERSION_REGEX.groups == 1, f"{NAME_REGEX.groups=}."

# NOTE: to get a list of extras, match NAME_PATTERN with EXTRAS_PATTERN
EXTRAS = rf"""\[\s*(?:{NAME})(?:\s*,{NAME})*\s*\]"""
EXTRAS_GROUP = rf"""(?P<extras>{EXTRAS})"""
EXTRAS_REGEX = re.compile(EXTRAS_GROUP)
assert EXTRAS_REGEX.groups == 1, f"{EXTRAS_REGEX.groups=}."

PROJECT_DEP = rf"""["']{NAME_GROUP}{EXTRAS}?\s*>=\s*{VERSION_GROUP}"""
PROJECT_DEP_GROUP = rf"""(?P<DEPENDENCY>{PROJECT_DEP})"""
PROJECT_DEP_REGEX = re.compile(PROJECT_DEP_GROUP)
assert PROJECT_DEP_REGEX.groups == 3, f"{PROJECT_DEP_REGEX.groups=}."

POETRY_DEP = rf"""{NAME_GROUP}\s*=\s*['"]\s*>=\s*{VERSION_GROUP}"""
POETRY_DEP_GROUP = rf"""(?P<DEPENDENCY>{POETRY_DEP})"""
POETRY_DEP_REGEX = re.compile(POETRY_DEP_GROUP)
assert POETRY_DEP_REGEX.groups == 3, f"{POETRY_DEP_REGEX.groups=}."

POETRY_EXT_DEP = (
    rf"""{NAME_GROUP}\s*=\s*\{{\s*version\s*=\s*['"]\s*>=\s*{VERSION_GROUP}\}}"""
)
POETRY_EXT_DEP_GROUP = rf"""(?P<DEPENDENCY>{POETRY_EXT_DEP})"""
POETRY_EXT_DEP_REGEX = re.compile(POETRY_DEP_GROUP)
assert POETRY_EXT_DEP_REGEX.groups == 3, f"{POETRY_EXT_DEP_REGEX.groups=}."


@cache
def get_pip_package_dict() -> dict[str, str]:
    """Construct dictionary package -> version."""
    output = subprocess.check_output(["pip", "list", "--format=json"])
    pip_list: list[dict[Literal["name", "version"], str]] = json.loads(output)
    return {pkg["name"].lower(): pkg["version"] for pkg in pip_list}


def strip_version(version: str, /) -> str:
    """Strip the version string to the first three parts."""
    sub = version.split(".")
    version = ".".join(sub[:3])
    # strip everything after the first non-numeric, non-dot character
    version = re.sub(r"[^0-9.].*", "", version)
    return version


def update_versions(raw_file: str, /, *, version_pattern: re.Pattern) -> str:
    """Update the dependencies in pyproject.toml according to version_pattern."""
    if version_pattern.groups != 3:
        raise ValueError(
            "version_pattern must have 3 groups (whole match, package name, version))"
            f" Got {version_pattern.groups} groups (pattern: {version_pattern.pattern})."
        )

    pkg_dict = get_pip_package_dict()

    # match all dependencies in the file
    for match, pkg, old_version in version_pattern.findall(raw_file):
        # get the new version from the pip list
        new_version = strip_version(pkg_dict.get(pkg, old_version))
        # if the version changed, replace the old version with the new one
        if old_version != new_version:
            new = match.replace(old_version, new_version)
            print(f"replacing: {match!r:36}  {new!r}")
            raw_file = raw_file.replace(match, new)
    return raw_file


def pyproject_update_dependencies(fname: str, /, *, debug: bool = False) -> None:
    """Update the dependencies in pyproject.toml."""
    with open(fname, "r", encoding="utf8") as file:
        pyproject = file.read()

    if debug:
        print(f"Processing {fname!r}")
        print(f"Installed packages: {get_pip_package_dict()}")

    # update [project.dependencies] and [project.optional-dependencies]
    pyproject = update_versions(pyproject, version_pattern=PROJECT_DEP_REGEX)

    # update [tool.poetry.dependencies] and [tool.poetry.group.<name>.dependencies]
    pyproject = update_versions(pyproject, version_pattern=POETRY_DEP_REGEX)

    # Update dependencies of the form `black = {version = ">=23.7.0", extras = ["d", "jupyter"]}`
    # NOTE: We assume that the version is always the first key in the table
    pyproject = update_versions(pyproject, version_pattern=POETRY_EXT_DEP_REGEX)

    with open(fname, "w", encoding="utf8") as file:
        # update the file
        file.write(pyproject)


def main() -> None:
    """Run the script."""
    parser = argparse.ArgumentParser(
        description="Updates the pyproject.toml dependencies to the currently installed versions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
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

    pyproject_update_dependencies(args.pyproject_file, debug=args.debug)


if __name__ == "__main__":
    main()
