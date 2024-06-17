#!/usr/bin/env python
r"""Prints the direct dependencies of a module line by line.

References:
    - https://peps.python.org/pep-0508/
    - https://peps.python.org/pep-0621/
    - https://packaging.python.org/en/latest/specifications/
    - https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#declaring-project-metadata
"""

# TODO: add support for extras.

__all__ = [
    # Type Aliases
    "Config",
    # Constants
    "STDLIB_MODULES",
    "NAME",
    "NAME_GROUP",
    "PACKAGES",
    "RE_NAME",
    "RE_NAME_GROUP",
    # Classes
    "GroupedDependencies",
    # Functions
    "calculate_dependencies",
    "check_file",
    "detect_dependencies",
    "get_module_dir",
    "get_deps_from_file",
    "get_deps_from_module",
    "get_deps_pyproject_project",
    "get_deps_pyproject_section",
    "get_deps_pyproject_tests",
    "get_name_pyproject",
    "group_dependencies",
    "main",
    "normalize",
]

import argparse
import ast
import importlib
import itertools
import os
import pkgutil
import re
import sys
import tomllib
from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from functools import cache
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType
from typing import Any, Optional, Self, TypeAlias

# NOTE: importlib.metadata is bugged in 3.10: https://github.com/python/cpython/issues/94113
if sys.version_info >= (3, 11):  # noqa: UP036
    from importlib import metadata
else:
    try:
        metadata = importlib.import_module("importlib_metadata")
    except ImportError as import_failed:
        import_failed.add_note(
            "This pre-commit hook runs in the local interpreter and requires importlib.metadata!"
            " Please use python≥3.11 or install 'importlib_metadata'."
        )
        raise

STDLIB_MODULES = sys.stdlib_module_names
r"""A set of all standard library modules."""

# https://peps.python.org/pep-0508/#names
# NOTE: we modify this regex a bit to allow to match inside context
RE_NAME = re.compile(r"""\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?\b""")
NAME = RE_NAME.pattern
RE_NAME_GROUP = re.compile(rf"""(?P<name>{NAME})""")
NAME_GROUP = RE_NAME_GROUP.pattern
assert RE_NAME_GROUP.groups == 1, f"{RE_NAME_GROUP.groups=}."

PACKAGES: dict[str, list[str]] = dict(metadata.packages_distributions())
r"""A dictionary that maps module names to their pip-package names."""

Config: TypeAlias = dict[str, Any]

# NOTE: illogical type hint in stdlib, maybe open issue.
# https://github.com/python/cpython/blob/608927b01447b110de5094271fbc4d49c60130b0/Lib/importlib/metadata/__init__.py#L933-L947C29
# https://github.com/python/typeshed/blob/d82a8325faf35aa0c9d03d9e9d4a39b7fcb78f8e/stdlib/importlib/metadata/__init__.pyi#L32


def normalize(dep: str, /) -> str:
    r"""Normalize a dependency name."""
    return dep.lower().replace("-", "_")


@cache
def get_module_dir(name: str, /) -> Path:
    r"""Get the directory of a module."""
    spec = find_spec(name)
    if spec is None or (origin := spec.origin) is None:
        raise ModuleNotFoundError(f"Failed to find module: {name!r}")
    path = Path(origin)
    assert path.is_file()
    return path.parent


def get_name_pyproject(config: Config, /) -> str:
    r"""Get the name of the project from pyproject.toml."""
    try:
        project_name = config["project"]["name"]
    except KeyError:
        project_name = NotImplemented
    try:
        poetry_name = config["tool"]["poetry"]["name"]
    except KeyError:
        poetry_name = NotImplemented

    match project_name, poetry_name:
        case str(a), str(b):
            if a != b:
                raise ValueError(
                    "Found inconsistent project names in [project] and [tool.poetry]."
                    f"\n [project]     is missing: {a}, "
                    f"\n [tool.poetry] is missing: {b}."
                )
            return a
        case str(a), _:
            return a
        case _, str(b):
            return b
        case _:
            raise ValueError("No project name found in [project] or [tool.poetry].")


def get_deps_pyproject_section(config: Config, /, *, section: str) -> set[str]:
    r"""Get the dependencies from a section of pyproject.toml.

    Looking up the section must either result in a list of strings or a dict.
    """
    conf: Any = config  # otherwise typing errors...

    try:  # recursively get the section
        for key in section.split("."):
            conf = conf[key]
    except KeyError:
        return NotImplemented

    match conf:
        # assume format `"package<comparator>version"`
        case list(lst):
            matches: set[str] = set()
            for dep in lst:
                match = re.search(RE_NAME, dep)
                if match is None:
                    raise ValueError(f"Invalid dependency: {dep!r}")
                matches.add(match.group())
            return matches
        # assume format `package = "<comparator>version"`
        case dict(dct):  # poetry
            return set(dct) - {"python"}
        case _:
            raise TypeError(f"Unexpected type: {type(config)}")


def get_deps_pyproject_project(config: Config, /) -> set[str]:
    r"""Extract the dependencies from a pyproject.toml file.

    There are 6 sections we check:
    - pyproject.dependencies
    - pyproject.optional-dependencies.test(s)
    - tool.poetry.dependencies
    - tool.poetry.group.test(s).dependencies

    If dependencies are specified in multiple sections, it is validated that they are
    the same.
    """
    dependencies = {
        key: get_deps_pyproject_section(config, section=key)
        for key in (
            "project.dependencies",
            "tool.poetry.dependencies",
        )
    }

    match (
        dependencies["project.dependencies"],
        dependencies["tool.poetry.dependencies"],
    ):
        case set(a), set(b):
            if (left := a - b) | (right := b - a):
                raise ValueError(
                    "Found inconsistent dependencies in [project] and [tool.poetry]."
                    f"\n [project]     is missing: {right}, "
                    f"\n [tool.poetry] is missing: {left}."
                )
            project_dependencies = a
        case set(a), _:
            project_dependencies = a
        case _, set(b):
            project_dependencies = b
        case _:
            project_dependencies = set()

    return project_dependencies


def get_deps_pyproject_tests(config: Config, /) -> set[str]:
    r"""Extract the test dependencies from a pyproject.toml file."""
    groups: dict[str, tuple[str, str]] = {
        "optional-dependencies": (
            "project.optional-dependencies.test",
            "project.optional-dependencies.tests",
        ),
        "poetry": (
            "tool.poetry.group.test.dependencies",
            "tool.poetry.group.tests.dependencies",
        ),
        "pdm": (
            "tool.pdm.dev-dependencies.test",
            "tool.pdm.dev-dependencies.tests",
        ),
    }

    dependencies = {  # NOTE: NotImplemented is used to indicate missing sections.
        section: get_deps_pyproject_section(config, section=section)
        for group in groups.values()
        for section in group
    }

    deps: dict[str, set[str]] = {}
    for group_name, (test_key, tests_key) in groups.items():
        match dependencies[test_key], dependencies[tests_key]:
            case set(), set():
                raise ValueError(f"Found both {test_key} and {tests_key}.")
            case set(left), _:
                deps[group_name] = left
            case _, set(right):
                deps[group_name] = right
            case _:
                pass

    # make sure test dependencies are consistent
    # iterate over all pairs:
    for (l_key, l_val), (r_key, r_val) in itertools.combinations(deps.items(), 2):
        if (missing_right := l_val - r_val) | (missing_left := r_val - l_val):
            raise ValueError(
                f"Found inconsistent test dependencies in pyproject.toml."
                f"\n {l_key:<20s} is missing, {missing_left=}."
                f"\n {r_key:<20s} is missing, {missing_right=}."
            )

    return set().union(*deps.values())


@dataclass
class GroupedDependencies:
    r"""A named tuple containing the dependencies grouped by type."""

    first_party: set[str] = field(default_factory=set)
    third_party: set[str] = field(default_factory=set)
    stdlib: set[str] = field(default_factory=set)

    def __or__(self, other: Self, /) -> "GroupedDependencies":
        return GroupedDependencies(
            first_party=self.first_party | other.first_party,
            third_party=self.third_party | other.third_party,
            stdlib=self.stdlib | other.stdlib,
        )

    def __ior__(self, other: Self, /) -> Self:
        self.first_party |= other.first_party
        self.third_party |= other.third_party
        self.stdlib |= other.stdlib
        return self


def group_dependencies(
    dependencies: set[str], /, *, filepath: Path
) -> GroupedDependencies:
    r"""Splits the dependencies into first-party and third-party.

    A dependency will be considered first-party, if its origin is a parent directory of path.
    """
    first_party_deps: set[str] = set()
    stdlib_deps: set[str] = set()
    third_party_deps: set[str] = set()
    assert filepath.is_file(), "Expected a file."

    for dependency in dependencies:
        if dependency in STDLIB_MODULES:
            stdlib_deps.add(dependency)
            continue

        try:
            module_dir = get_module_dir(dependency)
        except ModuleNotFoundError:
            third_party_deps.add(dependency)
        else:
            if filepath.is_relative_to(module_dir):
                first_party_deps.add(dependency)
            else:
                third_party_deps.add(dependency)

    return GroupedDependencies(
        first_party=first_party_deps,
        third_party=third_party_deps,
        stdlib=stdlib_deps,
    )


def detect_dependencies(
    fname: str | Path,
    /,
    *,
    ignore_private: bool = True,
) -> GroupedDependencies:
    r"""Collect the dependencies from files in the given path."""
    path = Path(fname)
    grouped_deps: GroupedDependencies = GroupedDependencies()

    if path.is_file():  # Single file
        deps = get_deps_from_file(path, ignore_private=ignore_private)
        grouped_deps |= group_dependencies(deps, filepath=path)
    elif path.is_dir():  # Directory
        for file_path in path.rglob("*.py"):
            grouped_deps |= detect_dependencies(file_path)
    else:  # assume module
        module_name = path.stem
        grouped_deps |= get_deps_from_module(module_name)
    # if not path.exists():
    #     raise FileNotFoundError(f"Invalid path: {path}")

    return grouped_deps


def get_deps_from_file(
    file_path: str | Path, /, *, ignore_private: bool = True
) -> set[str]:
    r"""Extract set of dependencies imported by a script."""
    path = Path(file_path)

    if path.suffix != ".py":
        raise ValueError(f"Invalid file extension: {path.suffix}")

    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=str(path))

    imported_modules: list[str] = []
    for node in ast.walk(tree):
        match node:
            case ast.Import(names=aliases):
                imported_modules.extend(alias.name for alias in aliases)
            case ast.ImportFrom(module=str(name)):
                imported_modules.append(name)

    # only keep the top-level module name
    dependencies: set[str] = set()
    for name in imported_modules:
        module_name = name.split(".")[0]
        if ignore_private and module_name.startswith("_"):
            continue
        dependencies.add(module_name)

    return dependencies


def get_deps_from_module(
    module_or_name: str | ModuleType,
    /,
    *,
    silent: bool = True,
) -> GroupedDependencies:
    r"""Extract set of dependencies imported by a module."""
    # NOTE: Generally there is no correct way to do it without importing the module.
    # This is because modules can be imported dynamically.
    match module_or_name:
        case ModuleType() as module:
            pass
        case str(name):
            with (  # load the submodule silently
                open(os.devnull, "w") as devnull,
                redirect_stdout(devnull if silent else sys.stdout),
                redirect_stderr(devnull if silent else sys.stderr),
            ):
                module = importlib.import_module(name)
        case _:
            raise TypeError(f"Invalid type: {type(module_or_name)}")

    # Visit the current module
    assert module.__file__ is not None
    deps = get_deps_from_file(module.__file__)
    grouped_deps = group_dependencies(deps, filepath=Path(module.__file__))

    if not hasattr(module, "__path__"):
        # note: can only recurse into packages.
        return grouped_deps

    # Visit the sub-packages/modules of the package
    # TODO: add dynamically imported submodules using the `pkgutil` module.
    for module_info in pkgutil.walk_packages(module.__path__):
        submodule_name = f"{module.__name__}.{module_info.name}"
        grouped_deps |= get_deps_from_module(submodule_name, silent=silent)

    return grouped_deps


def calculate_dependencies(
    *,
    imported_deps: set[str],
    declared_deps: set[str],
    excluded_deps: set[str],
    excluded_declared_deps: set[str],
    excluded_imported_deps: set[str],
) -> tuple[set[str], set[str], set[str]]:
    r"""Check the dependencies of a module.

    Args:
        imported_deps: The imported dependencies.
        declared_deps: The declared dependencies.
        excluded_deps: Dependencies to exclude, no matter what.
        excluded_declared_deps: Dependencies to exclude from the declared dependencies.
        excluded_imported_deps: Dependencies to exclude from the imported dependencies.
    """
    # map the imported dependencies to their pip-package names
    actual_deps: set[str] = set()
    missing_deps: set[str] = set()
    for dep in imported_deps:
        if dep not in PACKAGES:
            missing_deps.add(dep)
            continue

        mapped_deps = set(PACKAGES[dep])
        if len(mapped_deps) != 1:
            raise ValueError(f"Found multiple pip-packages for {dep!r}: {mapped_deps}.")

        actual_deps.add(mapped_deps.pop())

    # normalize the dependencies
    excluded_deps = set(map(normalize, excluded_deps))
    excluded_imported_deps = set(map(normalize, excluded_imported_deps))
    excluded_declared_deps = set(map(normalize, excluded_declared_deps))
    declared_deps = set(map(normalize, declared_deps)) - (
        excluded_declared_deps | excluded_deps
    )
    actual_deps = set(map(normalize, actual_deps)) - (
        excluded_imported_deps | excluded_deps
    )
    missing_deps = set(map(normalize, missing_deps)) - excluded_deps

    # check if all imported dependencies are listed in pyproject.toml
    undeclared_deps = actual_deps - declared_deps
    unused_deps = declared_deps - actual_deps

    return undeclared_deps, unused_deps, missing_deps


def check_file(
    fname: str | Path,
    /,
    *,
    module_dir: str = "src/",
    tests_dir: Optional[str] = "tests/",
    exclude: Sequence[str] = (),
    known_unused_deps: Sequence[str] = (),
    known_unused_test_deps: Sequence[str] = (),
    known_undeclared_deps: Sequence[str] = (),
    known_undeclared_test_deps: Sequence[str] = (),
    error_on_missing_deps: bool = True,
    error_on_missing_test_deps: bool = True,
    error_on_superfluous_test_deps: bool = True,
    error_on_undeclared_deps: bool = True,
    error_on_undeclared_test_deps: bool = True,
    error_on_unused_deps: bool = True,
    error_on_unused_test_deps: bool = False,
    debug: bool = False,
) -> int:
    r"""Check a single file."""
    violations = 0

    with open(fname, "rb") as file:
        config = tomllib.load(file)

    # get the normalized project name
    project_name = normalize(get_name_pyproject(config))
    # get dependencies from pyproject.toml
    declared_deps = get_deps_pyproject_project(config) | {project_name}
    # get test dependencies from pyproject.toml
    declared_test_deps = get_deps_pyproject_tests(config) | {project_name}
    # get superfluous test dependencies
    superfluous_test_deps = (declared_deps & declared_test_deps) - {project_name}
    # setup ignored dependencies
    excluded_deps = set(exclude)

    # region check project dependencies ------------------------------------------------
    # detect the imported dependencies from the source files
    detected_deps = detect_dependencies(module_dir)
    imported_deps = detected_deps.third_party
    first_party_deps = detected_deps.first_party
    # get the normalized project name
    undeclared_deps, unused_deps, missing_deps = calculate_dependencies(
        imported_deps=imported_deps,
        declared_deps=declared_deps,
        excluded_deps=excluded_deps,
        excluded_declared_deps=set(known_unused_deps),
        excluded_imported_deps=set(known_undeclared_deps),
    )

    if undeclared_deps and error_on_undeclared_deps:
        violations += 1
        print(f"Detected undeclared dependencies: {undeclared_deps}")
    if unused_deps and error_on_unused_deps:
        violations += 1
        print(f"Detected unused dependencies: {unused_deps}")
    if missing_deps and error_on_missing_deps:
        violations += 1
        print(f"Detected missing dependencies: {missing_deps}")
    if violations:
        print(
            f"Detected dependencies in project {module_dir!s}:"
            f"\n\tdeclared_deps={sorted(declared_deps)}"
            f"\n\timported_deps={sorted(imported_deps)}"
            f"\n\texcluded_deps={sorted(excluded_deps)}"
            f"\n\tfirst_party_deps={sorted(first_party_deps)}"
        )
    # endregion check project dependencies ----------------------------------------------

    # region check test dependencies ---------------------------------------------------
    if tests_dir is None:
        return violations

    detected_test_deps = detect_dependencies(tests_dir)
    imported_test_deps = detected_test_deps.third_party
    first_party_test_deps = detected_test_deps.first_party
    # we can safely ignore any undeclared dependencies, if they are part of the declared
    # project dependencies.

    undeclared_test_deps, unused_test_deps, missing_test_deps = calculate_dependencies(
        imported_deps=imported_test_deps,
        declared_deps=declared_test_deps,
        excluded_deps=excluded_deps,
        excluded_declared_deps=set(known_unused_test_deps),
        excluded_imported_deps=declared_deps | set(known_undeclared_test_deps),
    )

    test_violations = 0
    if undeclared_test_deps and error_on_undeclared_test_deps:
        test_violations += 1
        print(f"Detected undeclared test dependencies: {undeclared_test_deps}.")
    if unused_test_deps and error_on_unused_test_deps:
        test_violations += 1
        print(f"Detected unused test dependencies: {unused_test_deps}.")
    if missing_test_deps and error_on_missing_test_deps:
        test_violations += 1
        print(f"Detected missing test dependencies: {missing_test_deps}.")
    if superfluous_test_deps and error_on_superfluous_test_deps:
        test_violations += 1
        print(f"Detected superfluous test dependencies: {superfluous_test_deps}.")
        print("These are redundant, as they are already project dependencies")
    if test_violations:
        print(
            f"Detected dependencies in tests {tests_dir!s}:"
            f"\n\tdeclared_test_deps={sorted(declared_test_deps)}"
            f"\n\timported_test_deps={sorted(imported_test_deps)}"
            f"\n\texcluded_deps={sorted(excluded_deps)}"
            f"\n\tfirst_party_test_deps={sorted(first_party_test_deps)}"
        )

    return violations + test_violations
    # endregion emit violations --------------------------------------------------------


def main() -> None:
    r"""Print the third-party dependencies of a module."""
    parser = argparse.ArgumentParser(
        description="Print the third-party dependencies of a module.",
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
        "--module-dir",
        default="src/",
        type=str,
        help="The folder of the module to check.",
    )
    parser.add_argument(
        "--tests-dir",
        default="tests/",
        type=str,
        help="The path to the test directories.",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        type=str,
        help="List of dependencies to exclude no matter what.",
    )
    parser.add_argument(
        "--known-unused-deps",
        default=[],
        nargs="*",
        type=str,
        help="List of used dependencies to ignore.",
    )
    parser.add_argument(
        "--known-unused-test-deps",
        default=[],
        nargs="*",
        type=str,
        help="List of used dependencies to ignore.",
    )
    parser.add_argument(
        "--known-undeclared-deps",
        default=[],
        nargs="*",
        type=str,
        help="List of undeclared project dependencies to ignore.",
    )
    parser.add_argument(
        "--known-undeclared-test-deps",
        default=[],
        nargs="*",
        type=str,
        help="List of undeclared test dependencies to ignore.",
    )
    # parser.add_argument(
    #     "--error-on-superfluous-deps",
    #     action=argparse.BooleanOptionalAction,
    #     default=True,
    #     help="Raise error if dependency is superfluous.",
    # )
    parser.add_argument(
        "--error-on-undeclared-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if dependency is undeclared.",
    )
    parser.add_argument(
        "--error-on-unused-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if dependency is unused.",
    )
    parser.add_argument(
        "--error-on-missing-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if dependency is missing (not installed).",
    )
    parser.add_argument(
        "--error-on-undeclared-test-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if test dependency is undeclared.",
    )
    parser.add_argument(
        "--error-on-superfluous-test-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if test dependency is superfluous.",
    )
    parser.add_argument(
        "--error-on-unused-test-deps",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Raise error if test dependency is unused.",
    )
    parser.add_argument(
        "--error-on-missing-test-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if dependency is not missing (not installed).",
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
            module_dir=args.module_dir,
            tests_dir=args.tests_dir,
            exclude=args.exclude,
            known_unused_deps=args.known_unused_deps,
            known_unused_test_deps=args.known_unused_test_deps,
            known_undeclared_deps=args.known_undeclared_deps,
            known_undeclared_test_deps=args.known_undeclared_test_deps,
            # error selection
            error_on_unused_deps=args.error_on_unused_deps,
            error_on_missing_deps=args.error_on_missing_deps,
            error_on_superfluous_test_deps=args.error_on_superfluous_test_deps,
            error_on_unused_test_deps=args.error_on_unused_test_deps,
            error_on_undeclared_deps=args.error_on_undeclared_deps,
            error_on_undeclared_test_deps=args.error_on_undeclared_test_deps,
            error_on_missing_test_deps=args.error_on_missing_test_deps,
            debug=args.debug,
        )
    except Exception as exc:
        exc.add_note(f"Checking file {args.pyproject_file!s} failed!")
        raise

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
