r"""Detects unmaintained dependencies."""

__all__ = [
    # Constants
    "VERSION_REGEX",
    # Functions
    "check_pyproject",
    "extract_names",
    "get_all_pypi_json",
    "get_dependencies_from_pyproject",
    "get_latest_version",
    "get_local_packages",
    "get_optional_dependencies_from_pyproject",
    "get_project_name_from_pyproject",
    "get_pypi_json",
    "get_release_date",
    "get_release_version",
    "is_canonical",
    "main",
]

import argparse
import asyncio
import importlib.metadata as importlib_metadata
import re
import tomllib
import warnings
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any, TypeAlias

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
    r"""Check if the given version is a canonical version."""
    return re.match(VERSION_REGEX, version) is not None


def _normalize(name: str, /) -> str:
    r"""Replace non-word characters with underscores and make lowercase."""
    return re.sub(r"\W", "_", name).lower()


async def get_pypi_json(pkg: str, /, *, session: aiohttp.ClientSession) -> JSON:
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
        return dict(zip(packages, responses, strict=True))


def get_release_version(version: str, /) -> tuple[int, ...]:
    r"""Get the release version as a tuple of integers."""
    match = re.match(VERSION_REGEX, version)
    if match is None:
        warnings.warn(f"Invalid version: {version}", stacklevel=2)
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


def extract_names(deps: list[str], /, *, normalize_names: bool = True) -> list[str]:
    r"""Simplify the dependencies by removing the version, duplicates, and normalizing."""
    # We are only interested in the name, not the version.
    # https://packaging.python.org/en/latest/specifications/dependency-specifiers/#names
    name_regex = re.compile(r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$")

    processed_deps = []
    for dep in deps:
        if match := name_regex.match(dep):
            processed_deps.append(match.group())
        else:
            raise ValueError(f"Invalid dependency name: {dep!r}")

    if normalize_names:
        processed_deps = [_normalize(dep) for dep in processed_deps]

    # remove duplicates and sort
    return sorted(set(processed_deps))


def get_project_name_from_pyproject(
    pyproject: dict, /, *, normalize: bool = True
) -> str:
    r"""Extracts the project name from the pyproject.toml file."""
    try:
        project_name = pyproject["project"]["name"]
    except KeyError as exc:
        exc.add_note("Cannot find project name in pyproject.toml.")
        raise

    if normalize:
        return _normalize(project_name)

    return project_name


def get_dependencies_from_pyproject(
    pyproject: dict, /, *, normalize: bool = True
) -> list[str]:
    r"""Extracts the dependencies from the pyproject.toml file.

    Args:
        pyproject (dict): The parsed pyproject.toml file.
        normalize (bool, optional):
            If true, normalizes the package names (lowercase, underscores).
            Defaults to True.
    """
    try:
        raw_dependencies = pyproject["project"]["dependencies"]
    except KeyError as exc:
        exc.add_note("Cannot find dependencies in pyproject.toml.")
        raise

    return extract_names(raw_dependencies, normalize_names=normalize)


def get_optional_dependencies_from_pyproject(
    pyproject: dict, /, *, normalize: bool = True, error_on_missing: bool = False
) -> list[str]:
    r"""Extracts the optional dependencies from the pyproject.toml file.

    Args:
        pyproject (dict): The parsed pyproject.toml file.
        normalize (bool, optional):
            If true, normalizes the package names (lowercase, underscores).
            Defaults to True.
        error_on_missing (bool, optional):
            If true, raises an error if the optional-dependencies key is missing.
            Defaults to False.
    """
    try:
        raw_optional_deps = pyproject["project"]["optional-dependencies"]
    except KeyError as exc:
        if error_on_missing:
            exc.add_note("Cannot find optional-dependencies in pyproject.toml.")
            raise
        else:
            return []

    # concatenate the lists
    raw_optional_deps = list(set().union(*raw_optional_deps))

    return extract_names(raw_optional_deps, normalize_names=normalize)


def get_local_packages() -> dict[str, tuple[str, str, str]]:
    r"""Get the packages installed in the current environment."""
    packages = {
        x.name: (
            x.version,
            x.metadata["Summary"],
            x.metadata["License"],
        )
        for x in importlib_metadata.distributions()
    }
    return packages


def check_pyproject(
    filename: str,
    /,
    *,
    threshold: int,
    check_optional: bool,
    check_unlisted: bool,
) -> int:
    r"""Check the pyproject.toml file for unmaintained dependencies."""
    threshold_date = datetime.now() - timedelta(days=threshold)

    # load the pyproject.toml as dict
    with open(filename, "rb") as file:
        pyproject = tomllib.load(file)

    project_name = get_project_name_from_pyproject(pyproject)
    project_dependencies = get_dependencies_from_pyproject(pyproject)
    project_optional_deps = get_optional_dependencies_from_pyproject(pyproject)

    # get local packages
    local_packages = get_local_packages()

    # get the latest versions of all packages
    pypi_packages = asyncio.run(get_all_pypi_json(local_packages))
    latest_versions = {
        pkg: get_latest_version(pkg_metadata)
        for pkg, pkg_metadata in pypi_packages.items()
    }

    # check which packages are unmaintained
    unmaintained_packages: list[str] = [
        pkg
        for pkg, (_, upload_date) in latest_versions.items()
        if upload_date < threshold_date
    ]
    # normalize the names
    unmaintained_packages = extract_names(unmaintained_packages)
    # exclude the project itself
    unmaintained_packages.remove(project_name)

    # Split unmaintained packages into 3 groups:
    #   1. direct dependencies (listed in pyproject.toml)
    #   2. optional dependencies (listed in pyproject.toml)
    #   3. other dependencies (not listed in pyproject.toml)
    # NOTE: We need to normalize names!

    violations = 0
    if check_unlisted:
        for pkg in unmaintained_packages:
            latest_version, upload_date = latest_versions[pkg]
            violations += 1
            print(
                f"Dependency {pkg} appears unmaintained "
                f"(latest version={latest_version} from {upload_date}"
            )
        return violations

    if check_optional:
        for pkg in set(unmaintained_packages) & set(project_optional_deps):
            latest_version, upload_date = latest_versions[pkg]
            violations += 1
            print(
                f"Optional dependency {pkg} appears unmaintained "
                f"(latest version={latest_version} from {upload_date}"
            )

    for pkg in set(unmaintained_packages) & set(project_dependencies):
        latest_version, upload_date = latest_versions[pkg]
        violations += 1
        print(
            f"Dependency {pkg} appears unmaintained "
            f"(latest version={latest_version} from {upload_date}"
        )

    return violations


def main() -> None:
    r"""Run the main script."""
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
        "--check-optional",
        "-o",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="If true, checks optional dependencies.",
    )
    parser.add_argument(
        "--check-unlisted",
        "-u",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="If true, check all local packages.",
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
            check_optional=args.check_optional,
            check_unlisted=args.check_unlisted,
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