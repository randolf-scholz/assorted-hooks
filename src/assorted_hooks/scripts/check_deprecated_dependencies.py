import argparse
import asyncio
import importlib.metadata
import re
import tomllib
import warnings
from datetime import datetime, timedelta
from typing import Any, Iterable, TypeAlias

import aiohttp

JSON: TypeAlias = dict[str, Any]


# https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
VERSION_REGEX = re.compile(
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
r"""Regular expression for parsing version strings."""


def is_canonical(version: str, /) -> bool:
    return re.match(VERSION_REGEX, version) is not None


def _normalize(name: str, /) -> str:
    """Replace non-word characters with underscores and make lowercase."""
    return re.sub(r"\W", "_", name).lower()


async def get_pypi_json(pkg: str, /, session: aiohttp.ClientSession) -> JSON:
    r"""Get the JSON data for the given package."""
    url = f"https://pypi.org/pypi/{pkg}/json"
    async with session.get(url) as response:
        match response.status:
            case 200:
                return await response.json()
            case 404:
                raise ValueError(f"Package {pkg!r} not found.")
            case status:
                raise ValueError(f"Failed to get package {pkg!r}: {status=}")


async def get_all_pypi_json(packages: Iterable[str], /) -> dict[str, JSON]:
    r"""Get the JSON data for all the given packages."""
    async with aiohttp.ClientSession() as session:
        tasks = (get_pypi_json(pkg, session=session) for pkg in packages)
        responses = await asyncio.gather(*tasks)
        return {pkg: data for pkg, data in zip(packages, responses)}


def get_release_version(version: str, /) -> tuple[int, ...]:
    r"""Get the release version as a tuple of integers."""
    match = re.match(VERSION_REGEX, version)
    if match is None:
        warnings.warn(f"Invalid version: {version}")
        return (0,)
    return tuple(int(x) for x in match.group("release").split("."))


def get_release_date(releases: list[JSON], /) -> datetime:
    r"""Get the upload date of the earliest release."""
    uploads = [datetime.fromisoformat(release["upload_time"]) for release in releases]
    if not uploads:
        raise ValueError("No uploads found.")
    return min(uploads)


def get_latest_version(metadata: JSON, /) -> tuple[str, datetime]:
    r"""Get the latest version and upload date of the given package."""
    releases: dict[str, list[JSON]] = metadata["releases"]

    # pick the release with the highest version number
    sorted_releases = sorted(releases, key=get_release_version)
    latest_release = sorted_releases[-1]

    # one release can have multiple uploads (windows, mac, linux, etc.)
    # we choose the earliest upload
    release_uploads = releases[latest_release]
    upload_date = get_release_date(release_uploads)

    return latest_release, upload_date


def get_local_packages() -> dict[str, tuple[str, str, str]]:
    r"""Get the packages installed in the current environment."""
    packages = {
        x.name: (
            x.version,
            x.metadata["Summary"],
            x.metadata["License"],
        )
        for x in importlib.metadata.distributions()
    }
    return packages


def check_pyproject(filename: str, *, recursive: bool, threshold: int) -> int:
    # load the pyproject.toml as dict
    with open(filename, "rb") as file:
        pyproject = tomllib.load(file)

    # load the pyproject.toml as string
    with open(filename, encoding="utf8") as file:
        pyproject = file.read()

    try:  # get the name
        project_name = pyproject["project"]["name"]
    except KeyError as exc:
        exc.add_note("Cannot find project name in pyproject.toml.")
        raise

    try: # get the dependencies
        pyproject_dependencies = pyproject["project"]["dependencies"]
    except KeyError as exc:
        exc.add_note("Cannot find dependencies in pyproject.toml.")
        raise

    # get local packages
    local_packages = get_local_packages()
    # exclude the current project
    local_packages.pop(project_name, None)
    if not recursive:
        # remove all packages that are not direct dependencies
        for pkg in pyproject["project"]["dependencies"]:



    pypi_packages = asyncio.run(get_all_pypi_json(local_packages))
    latest_versions = {
        pkg: get_latest_version(pkg_metadata)
        for pkg, pkg_metadata in pypi_packages.items()
    }

    threshold = datetime.now() - timedelta(days=threshold)

    # check which packages are deprecated
    deprecated_packages: list[str] = [
        pkg
        for pkg, (_, upload_date) in latest_versions.items()
        if upload_date < threshold
    ]

    # regex check for deprecated packages
    pkg_regex = re.compile(rf"""({
        "|".join(rf"(?P<{_normalize(name)}>{name})" for name in deprecated_packages)
    })""")
    violations = 0
    for i, line in enumerate(pyproject.split("\n"), start=1):
        if match := pkg_regex.search(line):
            violations += 1
            print(f"pyproject.toml:{i}: {line} ({match.group()})")
    return violations


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Checks for unmaintained dependencies.",
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
        "--threshold",
        type=int,
        default=1000,
        help="Threshold for the number of days since the last release.",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="If true, checks dependencies recursively.",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Print debug information.",
    )
    args = parser.parse_args()

    try:
        violations = check_pyproject(
            args.pyproject_file,
            recursive=args.recursive,
            threshold=args.threshold,
        )
    except Exception as exc:
        exc.add_note(f'Checking file "{args.pyproject_file!s}" failed!')
        raise

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
