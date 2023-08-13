#!/usr/bin/env python
"""Updates the pyproject.toml dependencies to the currently installed versions."""


__all__ = [
    "get_pip_package_dict",
    "main",
    "process_pyproject",
    "strip_version",
    "update_versions",
]

import argparse
import json
import re
import subprocess
from functools import cache
from typing import Literal


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


def process_pyproject(fname: str, /, *, debug: bool = False) -> None:
    with open(fname, "r", encoding="utf8") as file:
        pyproject = file.read()

    if debug:
        print(f"Processing {fname!r}")
        print(f"Installed packages: {get_pip_package_dict()}")

    # update pyproject.dependencies
    pyproject_pattern = re.compile(r'"(([a-zA-Z0-9_-]*)>=([0-9.]*)")')
    pyproject = update_versions(pyproject, version_pattern=pyproject_pattern)

    # update tool.poetry.dependencies
    poetry_pattern = re.compile(r'(([a-zA-Z0-9_-]*) = ">=([0-9.]*)")')
    pyproject = update_versions(pyproject, version_pattern=poetry_pattern)

    # needed for things like `black = {version = ">=23.7.0", extras = ["d", "jupyter"]}`
    version_pattern = re.compile(r'(([a-zA-Z0-9_-]*) = \{\s?version = ">=([0-9.]*)")')
    pyproject = update_versions(pyproject, version_pattern=version_pattern)

    with open(fname, "w", encoding="utf8") as file:
        # update the file
        file.write(pyproject)


def main() -> None:
    """Run the script."""
    parser = argparse.ArgumentParser(
        description="Updates the pyproject.toml dependencies to the currently installed versions."
    )
    parser.add_argument(
        "file",
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

    process_pyproject(args.file, debug=args.debug)


if __name__ == "__main__":
    main()
