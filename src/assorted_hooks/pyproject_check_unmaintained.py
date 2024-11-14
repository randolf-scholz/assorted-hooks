#!/usr/bin/env python
r"""Detects unmaintained dependencies."""

# TODO: add check if repo is archived

__all__ = [
    # Constants
    "TIMEOUT",
    # Classes
    "Spec",
    # Functions
    "check_file",
    "check_pyproject",
    "get_all_pypi_json",
    "get_latest_release",
    "get_local_packages",
    "get_project_name_from_pyproject",
    "get_pypi_fallback",
    "get_pypi_json",
    "get_release_date",
    "main",
]

import argparse
import asyncio
import importlib.metadata as importlib_metadata
import json
import tomllib
import warnings
from collections.abc import Iterable
from datetime import datetime, timedelta
from functools import partial
from typing import Any, NamedTuple, TypeAlias
from urllib.request import urlopen

from packaging.utils import NormalizedName, canonicalize_name

from assorted_hooks.utils import (
    get_canonical_names,
    get_dev_requirements_from_pyproject,
    get_requirements_from_pyproject,
)

JSON: TypeAlias = dict[str, Any]
TIMEOUT = 3  # seconds


class Spec(NamedTuple):
    r"""Package specification."""

    version: str
    summary: str
    license: str


async def get_pypi_json(pkg: str, /, *, session: Any) -> JSON:
    r"""Get the JSON data for the given package."""
    url = f"https://pypi.org/pypi/{pkg}/json"
    async with session.get(url, timeout=TIMEOUT) as response:
        match response.status:
            case 200:
                return await response.json()
            case 404:
                raise ValueError(f"Package {pkg!r} not found.")
            case status:
                raise ValueError(f"Failed to get package {pkg!r}: {status=}")


async def get_pypi_fallback(pkg: str, /) -> JSON:
    url = f"https://pypi.org/pypi/{pkg}/json"
    loop = asyncio.get_event_loop()
    getter = partial(urlopen, timeout=TIMEOUT)
    response = await loop.run_in_executor(None, getter, url)
    match response.status:
        case 200:
            return json.load(response)
        case 404:
            raise ValueError(f"Package {pkg!r} not found.")
        case status:
            raise ValueError(f"Failed to get package {pkg!r}: {status=}")


async def get_all_pypi_json(packages: Iterable[str], /) -> dict[str, JSON]:
    r"""Get the JSON data for all the given packages."""
    try:  # load aiohttp if available
        import aiohttp
    except (ImportError, ModuleNotFoundError):
        warnings.warn("aiohttp is not available, using fallback.", stacklevel=2)
        tasks = (get_pypi_fallback(pkg) for pkg in packages)
        responses = await asyncio.gather(*tasks)
    else:
        async with aiohttp.ClientSession() as session:
            tasks = (get_pypi_json(pkg, session=session) for pkg in packages)
            responses = await asyncio.gather(*tasks)

    return dict(zip(packages, responses, strict=True))


def get_release_date(releases: list[JSON], /) -> datetime:
    r"""Get the upload date of the earliest release."""
    uploads = [datetime.fromisoformat(release["upload_time"]) for release in releases]
    return min(uploads, default=datetime.min)


def get_latest_release(metadata: JSON, /) -> tuple[str, datetime]:
    r"""Get the latest version and upload date of the given package."""
    releases: dict[str, list[JSON]] = metadata["releases"]

    # pick the latest release
    upload_dates: dict[str, datetime] = {}
    for version, release in releases.items():
        upload_dates[version] = get_release_date(release)

    # pick the most recent release
    latest_release: str = max(upload_dates, key=upload_dates.__getitem__)

    return latest_release, upload_dates[latest_release]


def get_project_name_from_pyproject(pyproject: dict, /) -> NormalizedName:
    r"""Extracts the project name from the pyproject.toml file."""
    try:
        project_name = pyproject["project"]["name"]
    except KeyError as exc:
        exc.add_note("Cannot find project name in pyproject.toml.")
        raise
    return canonicalize_name(project_name)


def get_local_packages() -> dict[NormalizedName, tuple[str, str, str]]:
    r"""Get the packages installed in the current environment."""
    return {
        canonicalize_name(x.name): (
            x.version,
            x.metadata["Summary"],
            x.metadata["License"],
        )
        for x in importlib_metadata.distributions()
    }


def check_pyproject(
    pyproject: JSON,
    /,
    *,
    check_optional: bool = True,
    check_unlisted: bool = False,
    threshold: int = 1000,
) -> int:
    r"""Check the pyproject.toml file for unmaintained dependencies."""
    threshold_date = datetime.now() - timedelta(days=threshold)

    # extract project name and dependencies (normalizing names)
    project_name = get_project_name_from_pyproject(pyproject)
    project_main_deps: list[NormalizedName] = sorted(
        canonicalize_name(req.name)
        for req in get_requirements_from_pyproject(pyproject)
    )
    project_dev_deps: list[NormalizedName] = sorted(
        canonicalize_name(req.name)
        for req in get_dev_requirements_from_pyproject(pyproject)
    )
    local_packages: list[NormalizedName]

    # get local packages
    if check_unlisted:
        local_packages = sorted(get_local_packages())
        # exclude the project itself
        if project_name in local_packages:
            local_packages.remove(project_name)
        # add missing declared dependencies
        for dep in project_main_deps + project_dev_deps:
            if dep not in local_packages:
                warnings.warn(
                    f"Dependency {dep!r} appears to not be installed.",
                    stacklevel=2,
                )
                local_packages.append(dep)
    else:
        local_packages = project_main_deps + project_dev_deps

    # get the latest versions of all packages
    pypi_packages: dict[str, JSON] = asyncio.run(get_all_pypi_json(local_packages))
    latest_releases: dict[NormalizedName, tuple[str, datetime]] = {}
    for pkg, pkg_metadata in pypi_packages.items():
        try:
            latest_release = get_latest_release(pkg_metadata)
        except Exception as exc:
            exc.add_note(
                f"Failed to get latest release for {pkg!r}"
                f"\n{local_packages=}"
                f"\n{project_name=}"
                f"\n{project_main_deps=}"
                f"\n{project_dev_deps=}"
            )
            raise
        name = canonicalize_name(pkg)
        latest_releases[name] = latest_release

    # check which packages are unmaintained
    unmaintained_packages: set[NormalizedName] = {
        pkg
        for pkg, (_, upload_date) in latest_releases.items()
        if upload_date < threshold_date
    }
    # normalize the names
    unmaintained_packages = get_canonical_names(unmaintained_packages)
    bad_direct_deps = unmaintained_packages & set(project_main_deps)
    bad_optional_deps = unmaintained_packages & set(project_dev_deps)
    bad_unlisted_deps = unmaintained_packages - (bad_direct_deps | bad_optional_deps)

    # Split unmaintained packages into 3 groups:
    #   1. direct dependencies (listed in pyproject.toml)
    #   2. optional dependencies (listed in pyproject.toml)
    #   3. other dependencies (not listed in pyproject.toml)
    # NOTE: We need to normalize names!

    violations = 0
    for pkg in bad_direct_deps:
        latest_version, upload_date = latest_releases[pkg]
        violations += 1
        print(
            f"Direct dependency {pkg!r} appears unmaintained "
            f"(latest release: {latest_version} from {upload_date})"
        )

    if check_optional:
        for pkg in bad_optional_deps:
            latest_version, upload_date = latest_releases[pkg]
            violations += 1
            print(
                f"Optional dependency {pkg!r} appears unmaintained "
                f"(latest release: {latest_version} from {upload_date})"
            )

    if check_unlisted:
        for pkg in bad_unlisted_deps:
            latest_version, upload_date = latest_releases[pkg]
            violations += 1
            print(
                f"Unlisted dependency {pkg!r} appears unmaintained "
                f"(latest release: {latest_version} from {upload_date})"
            )

    return violations


def check_file(filename: str, /, **opts: Any) -> int:
    r"""Check the pyproject.toml file for unmaintained dependencies."""
    # load the pyproject.toml as dict
    with open(filename, "rb") as file:
        pyproject = tomllib.load(file)

    return check_pyproject(pyproject, **opts)


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
        violations = check_file(
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
