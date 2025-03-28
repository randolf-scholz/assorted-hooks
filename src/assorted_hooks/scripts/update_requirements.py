#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# ///
# ruff: noqa: S101
r"""Update dependencies in pyproject.toml to the currently installed versions.

Note:
    Needs to be run as script since it needs to execute `pip` from the target environment.

References:
    - (Final) PEP 440 – Version Identification and dependency Specification
      https://peps.python.org/pep-0440/
    - (Final) PEP 508 – dependency specification for Python Software Packages
      https://peps.python.org/pep-0508/
    - (Final) PEP 621 – Storing project metadata in pyproject.toml
      https://peps.python.org/pep-0621/
    - (Superseded) PEP 631 – dependency specification in pyproject.toml based on PEP 508
      https://peps.python.org/pep-0631/
    - (Rejected) PEP 633 – dependency specification in pyproject.toml using an exploded TOML table
      https://peps.python.org/pep-0633/
"""

__all__ = [
    # CONSTANTS COLLECTIONS
    "PATTERNS",
    "REGEXPS",
    # PATTERNS
    "EXTRAS",
    "EXTRAS_GROUP",
    "NAME",
    "NAME_GROUP",
    "POETRY_DEP",
    "POETRY_DEP_GROUP",
    "PROJECT_DEP",
    "PROJECT_DEP_GROUP",
    "URI",
    "URI_GROUP",
    "URL",
    "URL_GROUP",
    "VERSION",
    "VERSION_GROUP",
    "VERSION_NUMERIC",
    "VERSION_NUMERIC_GROUP",
    # REGEXPS
    "RE_EXTRAS",
    "RE_EXTRAS_GROUP",
    "RE_NAME",
    "RE_NAME_GROUP",
    "RE_POETRY_DEP",
    "RE_POETRY_DEP_GROUP",
    "RE_PROJECT_DEP",
    "RE_PROJECT_DEP_GROUP",
    "RE_URI",
    "RE_URI_GROUP",
    "RE_URL",
    "RE_URL_GROUP",
    "RE_VERSION",
    "RE_VERSION_GROUP",
    "RE_VERSION_NUMERIC",
    "RE_VERSION_NUMERIC_GROUP",
    # CONSTANTS
    "PKG_DICT",
    # Types
    "PypiName",
    # Functions
    "canonicalize_name",
    "ignore_subgroups",
    "is_dependency_pattern",
    "main",
    "check_file",
    "strip_version",
    "update_versions",
]

import argparse
import logging
import re
from importlib.metadata import distributions
from pathlib import Path
from re import Pattern
from typing import NewType, cast

_LOGGER = logging.getLogger(__name__)


PypiName = NewType("PypiName", str)
r"""A type hint for PyPI package names."""


def canonicalize_name(name: str, /) -> PypiName:
    r"""Normalize the name of a package (PEP 503)."""
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    return cast("PypiName", normalized)


PKG_DICT: dict[PypiName, str] = {
    canonicalize_name(dist.metadata["Name"]): dist.version for dist in distributions()
}
r"""A dictionary of installed packages."""


def ignore_subgroups(pattern: str | Pattern, /) -> str:
    r"""Ignore all named groups in the given pattern."""
    pattern = pattern if isinstance(pattern, str) else pattern.pattern
    return re.sub(r"\(\?P<[^>]+>", r"(?:", pattern)


def is_dependency_pattern(pattern: str | Pattern, /) -> bool:
    r"""Check whether the pattern includes the 3 named groups {'dependency', 'name', 'version'}."""
    if not isinstance(pattern, Pattern):
        pattern = re.compile(pattern)
    return {"dependency", "name", "version"} <= pattern.groupindex.keys()


# region PATTERNS ----------------------------------------------------------------------
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

RE_VERSION_NUMERIC = re.compile(r"""[0-9]+(?:[.][0-9]+)*""")
VERSION_NUMERIC = RE_VERSION_NUMERIC.pattern
RE_VERSION_NUMERIC_GROUP = re.compile(rf"""(?P<version>{VERSION_NUMERIC})""")
VERSION_NUMERIC_GROUP = RE_VERSION_NUMERIC_GROUP.pattern

# https://peps.python.org/pep-0508/#names
# NOTE: we modify this regex a bit to allow to match inside context
RE_NAME = re.compile(r"""\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?\b""")
NAME = RE_NAME.pattern
RE_NAME_GROUP = re.compile(rf"""(?P<name>{NAME})""")
NAME_GROUP = RE_NAME_GROUP.pattern
assert RE_NAME_GROUP.groups == 1, f"{RE_NAME_GROUP.groups=}."

# NOTE: to get a list of extras, match NAME_PATTERN with EXTRAS_PATTERN
RE_EXTRAS = re.compile(rf"""(?:\[\s*)(?:{NAME})(?:\s*,{NAME})*(?:\s*\])""")
EXTRAS = RE_EXTRAS.pattern
RE_EXTRAS_GROUP = re.compile(rf"""(?P<extras>{EXTRAS})""")
EXTRAS_GROUP = RE_EXTRAS_GROUP.pattern
assert RE_EXTRAS_GROUP.groups == 1, f"{RE_EXTRAS_GROUP.groups=}."

# for dependencies like ``name [fred,bar] @ http://foo.com ; python_version=='2.7'``
RE_URL = re.compile(r"""\b[\w:/-]+\b""")
URL = RE_URL.pattern
RE_URL_GROUP = re.compile(rf"""(?P<url>{URL})""")
URL_GROUP = RE_URL_GROUP.pattern
# URI
RE_URI = re.compile(rf"""\s*@\s*{URL_GROUP}\s*""")
URI = RE_URI.pattern
RE_URI_GROUP = re.compile(rf"""(?P<uri>{URI})""")
URI_GROUP = RE_URI_GROUP.pattern

RE_PROJECT_DEP = re.compile(
    rf"""["']{NAME_GROUP}{EXTRAS_GROUP}?(?:\s*>=\s*){VERSION_GROUP}"""
)
PROJECT_DEP = RE_PROJECT_DEP.pattern
RE_PROJECT_DEP_GROUP = re.compile(rf"""(?P<dependency>{PROJECT_DEP})""")
PROJECT_DEP_GROUP = RE_PROJECT_DEP_GROUP.pattern
assert is_dependency_pattern(RE_PROJECT_DEP_GROUP), (
    f"{RE_PROJECT_DEP_GROUP.groupindex=}."
)

RE_POETRY_DEP = re.compile(rf"""(?x:
        {NAME_GROUP}
        (?:\s*=\s*)
        (?:{{\s*version\s*=\s*)?   # deps of the form `black = {{version = ">=23.7.0", extras = ["d"]}}`
        (?:['"]\s*>=\s*)
        {VERSION_GROUP}
    )""")
POETRY_DEP = RE_POETRY_DEP.pattern
RE_POETRY_DEP_GROUP = re.compile(rf"""(?P<dependency>{POETRY_DEP})""")
POETRY_DEP_GROUP = RE_POETRY_DEP_GROUP.pattern
assert is_dependency_pattern(RE_POETRY_DEP_GROUP), (
    f"{RE_PROJECT_DEP_GROUP.groupindex=}."
)

PATTERNS: dict[str, str] = {
    "EXTRAS": EXTRAS,
    "EXTRAS_GROUP": EXTRAS_GROUP,
    "NAME": NAME,
    "NAME_GROUP": NAME_GROUP,
    "POETRY_DEP": POETRY_DEP,
    "POETRY_DEP_GROUP": POETRY_DEP_GROUP,
    "PROJECT_DEP": PROJECT_DEP,
    "PROJECT_DEP_GROUP": PROJECT_DEP_GROUP,
    "URI": URI,
    "URI_GROUP": URI_GROUP,
    "URL": URL,
    "URL_GROUP": URL_GROUP,
    "VERSION": VERSION,
    "VERSION_GROUP": VERSION_GROUP,
    "VERSION_NUMERIC": VERSION_NUMERIC,
    "VERSION_NUMERIC_GROUP": VERSION_NUMERIC_GROUP,
}

REGEXPS: dict[str, Pattern] = {
    "RE_EXTRAS": RE_EXTRAS,
    "RE_EXTRAS_GROUP": RE_EXTRAS_GROUP,
    "RE_NAME": RE_NAME,
    "RE_NAME_GROUP": RE_NAME_GROUP,
    "RE_POETRY_DEP": RE_POETRY_DEP,
    "RE_POETRY_DEP_GROUP": RE_POETRY_DEP_GROUP,
    "RE_PROJECT_DEP": RE_PROJECT_DEP,
    "RE_PROJECT_DEP_GROUP": RE_PROJECT_DEP_GROUP,
    "RE_URI": RE_URI,
    "RE_URI_GROUP": RE_URI_GROUP,
    "RE_URL": RE_URL,
    "RE_URL_GROUP": RE_URL_GROUP,
    "RE_VERSION": RE_VERSION,
    "RE_VERSION_GROUP": RE_VERSION_GROUP,
    "RE_VERSION_NUMERIC": RE_VERSION_NUMERIC,
    "RE_VERSION_NUMERIC_GROUP": RE_VERSION_NUMERIC_GROUP,
}
# endregion Patterns -------------------------------------------------------------------


def strip_version(version: str, /) -> str:
    r"""Strip the version string to the first three parts."""
    # get numeric part of version
    numeric_version = re.search(RE_VERSION_NUMERIC_GROUP, version)
    if numeric_version is None:
        raise ValueError(f"Invalid version string: {version!r}.")
    return numeric_version.group("version")


def update_versions(
    raw_pyproject_file: str, /, *, dependency_pattern: str | Pattern
) -> str:
    r"""Update the dependencies in pyproject.toml according to version_pattern."""
    if not isinstance(dependency_pattern, Pattern):
        dependency_pattern = re.compile(dependency_pattern)

    if not is_dependency_pattern(dependency_pattern):
        raise ValueError(
            "dependency_pattern must include 3 named groups {'dependency', 'name', 'version'}."
            f" Got {dependency_pattern.groupindex=} instead."
        )

    # collect the new dependencies
    new_dependencies: dict[str, str] = {}
    # match all dependencies in the file
    for match in dependency_pattern.finditer(raw_pyproject_file):
        # extract the dependency, name, and version from the match
        groups = match.groupdict()
        dep: str = groups["dependency"]
        pkg_name: PypiName = canonicalize_name(groups["name"])
        old_version: str = groups["version"]

        # get the new version from the pip list
        new_version: str = PKG_DICT.get(pkg_name, old_version)

        # strip the version to the first three parts
        new_version = strip_version(new_version)

        # if the version changed, replace the old version with the new one
        if old_version != new_version:
            new_dependencies[dep] = dep.replace(old_version, new_version)

    # make a copy of the original content
    new_content = raw_pyproject_file
    max_key_len = max(map(len, new_dependencies), default=0)
    # iterate over the new dependencies
    for dep, new_dep in new_dependencies.items():
        print(f"{dep!r:<{max_key_len}} -> {new_dep!r}")
        new_content = new_content.replace(dep, new_dep)

    return new_content


def check_file(
    filepath: str | Path, /, *, autofix: bool = True, debug: bool = False
) -> int:
    r"""Update the dependencies in pyproject.toml."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    fname = str(path)
    original_pyproject = path.read_text(encoding="utf8")
    pyproject = original_pyproject

    if debug:
        print(f"Processing {fname!r}")
        print(f"Installed packages: {PKG_DICT}")

    # update [project.dependencies] and [project.optional-dependencies]
    pyproject = update_versions(pyproject, dependency_pattern=RE_PROJECT_DEP_GROUP)

    # update [tool.poetry.dependencies] and [tool.poetry.group.<name>.dependencies]
    pyproject = update_versions(pyproject, dependency_pattern=RE_POETRY_DEP_GROUP)

    if pyproject != original_pyproject:
        violations += 1

        if autofix:  # update the file
            path.write_text(pyproject, encoding="utf8")

    return violations


def main() -> None:
    r"""Run the script."""
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
        "--autofix",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically fix errors.",
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
        logging.basicConfig(level=logging.DEBUG)

    if args.autofix:
        print("Updating dependencies...")
    else:
        print("Checking dependencies (DRY RUN)...")

    try:
        violations = check_file(
            args.pyproject_file,
            autofix=args.autofix,
            debug=args.debug,
        )
    except Exception as exc:
        raise RuntimeError(f'Checking file "{args.pyproject_file!s}" failed!') from exc

    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
