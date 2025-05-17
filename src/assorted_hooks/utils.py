r"""Some utility functions for assorted_hooks."""

__all__ = [
    # Constants
    "REPO_REGEX",
    # Protocols
    "FileCheck",
    # Functions
    "get_canonical_names",
    "get_dev_requirements_from_pyproject",
    "get_path_relative_to_cwd",
    "get_path_relative_to_git_root",
    "get_python_files",
    "get_repository",
    "get_repository_name",
    "get_requirements_from_pyproject",
    "is_dunder",
    "is_private",
    "run_checks",
    "yield_deps",
    "yield_dev_deps",
]

import argparse
import logging
import re
import subprocess
import warnings
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from re import Pattern
from typing import Any, Optional, Protocol

from github import Github, RateLimitExceededException
from github.Repository import Repository
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import NormalizedName, canonicalize_name


def _iter_poetry_group(group: dict[str, Any], /) -> Iterator[str]:
    r"""Extracts the dependencies from a poetry group."""
    for key, value in group.items():
        if key == "python":
            continue
        match value:
            case str(spec):
                yield f"{key}{spec}"
            case {"version": str(version)}:
                yield f"{key}{version}"
            case _:
                yield key


def _iter_dep_group(group: Iterable[str | dict[str, Any]], /) -> Iterator[str]:
    """Iterate over the dependencies in a group.

    Note: [dependency-groups] allows {include-group = "group"} entries that we need to skip
    """
    for dep in group:
        if isinstance(dep, str):
            yield dep


def yield_deps(pyproject: dict, pattern: str | Pattern = "", /) -> Iterator[str]:
    r"""Yield the dependencies from the pyproject.toml file.

    Args:
        pyproject (dict): The parsed pyproject.toml file.
        pattern (str, optional):
            A regular expression pattern to match the group names.
            Applies to `[project.optional-dependencies]`.
            Pass impossible regex `(?!)` to not match any group.
    """
    # TODO: Add consistency check if multiple sections are realized
    regex = re.compile(pattern)

    # parse [project.dependencies]
    main_deps = pyproject.get("project", {}).get("dependencies", [])
    yield from main_deps

    # parse [project.optional-dependencies]
    optional_deps = pyproject.get("project", {}).get("optional-dependencies", {})
    for key, optional_group in optional_deps.items():
        if regex.match(key):
            yield from optional_group

    # parse [tool.poetry.dependencies]
    poetry_deps = pyproject.get("tool", {}).get("poetry", {}).get("dependencies", {})
    yield from _iter_poetry_group(poetry_deps)


def yield_dev_deps(pyproject: dict, pattern: str | Pattern = "", /) -> Iterator[str]:
    r"""Yield the development dependencies from the pyproject.toml file.

    Args:
        pyproject (dict): The parsed pyproject.toml file.
        pattern (str, optional):
            A regular expression pattern to match the group names.

    Extracts the dependencies from the following sections:
    - `dependency-groups`
    - `tool.pdm.dev-dependencies`
    - `tool.poetry.group.*.dependencies`
    """
    regex = re.compile(pattern)

    # parse [dependency-groups]
    dev_deps = pyproject.get("dependency-groups", {})
    for key, dep_group in dev_deps.items():
        if regex.match(key):
            yield from _iter_dep_group(dep_group)

    # parse [tool.pdm.dev-dependencies]
    pdm_deps = pyproject.get("tool", {}).get("pdm", {}).get("dev-dependencies", {})
    for key, pdm_group in pdm_deps.items():
        if regex.match(key):
            yield from pdm_group

    # parse [tool.poetry.group.*.dependencies]
    poetry_groups = pyproject.get("tool", {}).get("poetry", {}).get("group", {})
    for key, poetry_group in poetry_groups.items():
        if regex.match(key):
            poetry_deps = poetry_group.get("dependencies", {})
            yield from _iter_poetry_group(poetry_deps)


def get_requirements_from_pyproject(
    pyproject: dict, pattern: str | Pattern = "", /
) -> set[Requirement]:
    r"""Extracts the requirements from the pyproject.toml file.

    Args:
        pyproject (dict): The parsed pyproject.toml file.
        pattern (str, optional): A regex pattern to match the group names.
    """
    reqs: set[Requirement] = set()
    errors: dict[str, InvalidRequirement] = {}

    for dep in yield_deps(pyproject, pattern):
        try:
            req = Requirement(dep)
        except InvalidRequirement as exc:
            errors[dep] = exc
        else:
            reqs.add(req)

    if errors:
        raise RuntimeError("The following requirements are invalid:", list(errors))

    if not reqs:
        warnings.warn(
            "No requirements found in the pyproject.toml file.",
            stacklevel=2,
        )

    return reqs


def get_dev_requirements_from_pyproject(
    pyproject: dict, pattern: str | Pattern = "", /
) -> set[Requirement]:
    r"""Extracts the requirements from the pyproject.toml file.

    Args:
        pyproject (dict): The parsed pyproject.toml file.
        pattern (str, optional): A regex pattern to match the group names.
    """
    reqs: set[Requirement] = set()
    errors: dict[str, InvalidRequirement] = {}

    for dep in yield_dev_deps(pyproject, pattern):
        try:
            req = Requirement(dep)
        except InvalidRequirement as exc:
            errors[dep] = exc
        else:
            reqs.add(req)

    if errors:
        raise RuntimeError("The following requirements are invalid:", list(errors))

    if not reqs:
        warnings.warn(
            "No development requirements found in the pyproject.toml file.",
            stacklevel=2,
        )

    return reqs


def get_canonical_names(
    reqs: Iterable[str | Requirement], /
) -> frozenset[NormalizedName]:
    r"""Get the canonical names from a list of requirements."""
    return frozenset(
        canonicalize_name(r if isinstance(r, str) else r.name) for r in reqs
    )


REPO_REGEX = re.compile(r"github\.com/(?P<name>(?:[\w-]+/)*[\w-]+)(?:\.git)?")
r"""Regular expression to extract the repository name."""


def get_repository_name(url: str, /) -> str:
    r"""Extract the relevant information from a repository URL."""
    match = REPO_REGEX.search(url)
    if not match:
        raise ValueError(f"Could not extract repository information from {url!r}")
    return match.group("name")


def get_repository(git: Github, url: str, /) -> Repository:
    r"""Check if a repository is archived."""
    name = get_repository_name(url)
    try:
        repository = git.get_repo(name)
    except RateLimitExceededException:
        # TODO: Ask user for credentials and retry
        print("Rate limit exceeded!")
        raise SystemExit(1) from None
    except Exception as exc:
        raise RuntimeError(f"Could not get repository {name!r}!") from exc

    return repository


class FileCheck(Protocol):
    r"""Protocol for file checks."""

    def __call__(self, file: Path, /, *, options: argparse.Namespace) -> int: ...


def get_python_files(
    files_or_pattern: Iterable[str],
    /,
    *,
    root: Optional[Path] = None,
    raise_notfound: bool = True,
    relative_to_root: bool = False,
) -> list[Path]:
    r"""Get all python files from the given list of files or patterns."""
    paths: list[Path] = [Path(item).absolute() for item in files_or_pattern]

    # determine the root directory
    if root is None:
        root = (
            paths[0] if len(paths) == 1 and paths[0].is_dir() else Path.cwd().absolute()
        )

    files: list[Path] = []
    for path in paths:
        if path.exists():
            if path.is_file():
                files.append(path)
            if path.is_dir():
                files.extend(path.glob("**/*.py"))
            continue

        # else: path does not exist
        matches = list(root.glob(path.name))
        if not matches and raise_notfound:
            raise FileNotFoundError(f"Pattern {path!r} did not match any files.")
        files.extend(matches)

    if relative_to_root:
        files = [file.relative_to(root) for file in files]

    return files


def get_path_relative_to_cwd(path: Path, /) -> Path:
    r"""Get the relative path to the current working directory."""
    if path.is_relative_to(Path.cwd()):
        return path.relative_to(Path.cwd())
    return path


def get_path_relative_to_git_root(path: Path, /) -> Path:
    r"""Get the relative path to the git root directory.

    Raises:
        RuntimeError: If the git root directory could not be determined.
        ValueError: If the path is not inside the git repository.
    """
    output = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "--show-toplevel"], text=True
    )
    git_root = Path(output.strip())
    if not path.is_relative_to(git_root):
        raise ValueError(f"Path {path!r} is not inside the git repository!")
    return path.relative_to(git_root)


def run_checks(filespec: str, /, checker: Callable[[Path], int]) -> None:
    # find all files
    files: list[Path] = get_python_files(filespec)
    violations = 0
    exceptions = {}

    logger = logging.getLogger(checker.__module__)

    # apply script to all files
    for file in files:
        logger.debug('Checking "%s:0"', file)
        try:
            violations += checker(file)
        except Exception as exc:  # noqa: BLE001
            exceptions[file] = exc

    # display results
    print(f"{'-' * 79}\nFound {violations} violations.")

    if exceptions:
        excs = "\n".join(f"{key}: {value}" for key, value in exceptions.items())
        msg = f"{'-' * 79}\nChecking the following files failed!\n{excs}"
        raise ExceptionGroup(msg, list(exceptions.values()))

    if violations:
        raise SystemExit(1)


def is_dunder(name: str, /) -> bool:
    r"""Checks if the name is a dunder name."""
    return name.startswith("__") and name.endswith("__") and name.isidentifier()


def is_private(name: str, /) -> bool:
    r"""Checks if the name is a private name."""
    return name.startswith("_") and not name.startswith("__") and name.isidentifier()
