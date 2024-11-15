#!/usr/bin/env python
r"""Prints the direct dependencies of a module line by line.

Note:
    Needs to be run as script if module is imported.

References:
    - https://peps.python.org/pep-0508/
    - https://peps.python.org/pep-0621/
    - https://packaging.python.org/en/latest/specifications/
    - https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#declaring-project-metadata
"""

# TODO: add support for extras.

__all__ = [
    # Constants
    "STDLIB_MODULES",
    "PACKAGES",
    "SILENT",
    # Classes
    "GroupedRequirements",
    # Functions
    "resolve_dependencies",
    "check_file",
    "detect_dependencies",
    "get_module",
    "get_module_path",
    "get_requirement_origin",
    "get_requirements_from_ast",
    "get_requirements_from_module",
    "get_name_pyproject",
    "main",
]

import argparse
import ast
import importlib
import os
import pkgutil
import sys
import tomllib
from ast import Import, ImportFrom
from collections.abc import Iterator, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from functools import cache
from importlib import metadata
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType
from typing import Optional, Self

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import NormalizedName, canonicalize_name

from assorted_hooks.utils import (
    get_canonical_names,
    get_dev_requirements_from_pyproject,
    get_requirements_from_pyproject,
)

STDLIB_MODULES: frozenset[NormalizedName] = frozenset(
    map(canonicalize_name, sys.stdlib_module_names)
)
r"""A set of all standard library modules."""

PACKAGES: dict[NormalizedName, list[str]] = {
    canonicalize_name(key): val
    for key, val in metadata.packages_distributions().items()
}
r"""A dictionary that maps module names to their pip-package names."""

SILENT: bool = True
r"""Global flag to suppress output."""

# NOTE: illogical type hint in stdlib, maybe open issue.
# https://github.com/python/cpython/blob/608927b01447b110de5094271fbc4d49c60130b0/Lib/importlib/metadata/__init__.py#L933-L947C29
# https://github.com/python/typeshed/blob/d82a8325faf35aa0c9d03d9e9d4a39b7fcb78f8e/stdlib/importlib/metadata/__init__.pyi#L32


def yield_imports(tree: ast.AST, /) -> Iterator[str]:
    r"""Yield all imports from the tree."""
    for node in ast.walk(tree):
        match node:
            case Import(names=aliases):
                yield from (alias.name for alias in aliases)
            case ImportFrom(module=str(module)):
                yield module


@cache
def get_requirement_origin(req: Requirement | str, /) -> Path:
    r"""Get the directory of a module."""
    actual = Requirement(req) if isinstance(req, str) else req
    name = actual.name
    spec = find_spec(name)
    if spec is None or (origin := spec.origin) is None:
        raise ModuleNotFoundError(f"Failed to find module: {name!r}")

    if not spec.has_location:
        raise ModuleNotFoundError(f"Module {name!r} has no location.")

    path = Path(origin)
    if not path.is_file():
        raise FileNotFoundError(f"Invalid path: {path} is not a file!")

    return path.parent


def get_requirements_from_ast(
    tree: ast.AST, /, *, ignore_private: bool = True
) -> set[Requirement]:
    r"""Extract set of imported dependencies."""
    # only keep the top-level module name
    reqs: set[Requirement] = set()
    errors: dict[str, InvalidRequirement] = {}

    for name in yield_imports(tree):
        module_name = name.split(".")[0]
        if ignore_private and module_name.startswith("_"):
            continue

        try:
            req = Requirement(module_name)
        except InvalidRequirement as exc:
            errors[module_name] = exc
        else:
            reqs.add(req)
    return reqs


def get_requirements_from_module(module: ModuleType, /) -> set[Requirement]:
    r"""Extract set of dependencies imported by a module."""
    path = get_module_path(module)
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=str(path))
    reqs = get_requirements_from_ast(tree)
    return reqs


def get_module(module_or_name: str | ModuleType, /) -> ModuleType:
    r"""Get the module from the name or the module itself."""
    match module_or_name:
        case ModuleType() as module:
            return module
        case str(name):
            with (  # load the submodule silently
                open(os.devnull, "w", encoding="utf8") as devnull,
                redirect_stdout(devnull if SILENT else sys.stdout),
                redirect_stderr(devnull if SILENT else sys.stderr),
            ):
                module = importlib.import_module(name)
            return module
        case _:
            raise TypeError(f"Invalid type: {type(module_or_name)}")


def get_module_path(module: ModuleType, /) -> Path:
    r"""Get the path of a module."""
    if module.__file__ is None:
        raise ValueError(f"Invalid module: {module} has no __file__ attribute.")
    return Path(module.__file__)


@dataclass
class GroupedRequirements:
    r"""A named tuple containing the dependencies grouped by type.

    A requirement is considered first-party,
    if its origin is a parent directory of the path of the source (file or module).
    """

    first_party: set[Requirement] = field(default_factory=set)
    third_party: set[Requirement] = field(default_factory=set)
    stdlib: set[Requirement] = field(default_factory=set)

    @staticmethod
    def from_module(
        module: ModuleType, /, *, recursive: bool = False
    ) -> "GroupedRequirements":
        r"""Create grouped requirements from a module."""
        # extract the requirements from the module
        reqs = get_requirements_from_module(module)

        first_party_deps: set[Requirement] = set()
        stdlib_deps: set[Requirement] = set()
        third_party_deps: set[Requirement] = set()
        module_path = get_module_path(module)

        for req in reqs:
            if req.name in STDLIB_MODULES:
                stdlib_deps.add(req)
                continue

            try:
                req_path = get_requirement_origin(req)
            except ModuleNotFoundError:
                third_party_deps.add(req)
            else:
                if module_path.is_relative_to(req_path):
                    first_party_deps.add(req)
                else:
                    third_party_deps.add(req)

        grouped_reqs = GroupedRequirements(
            first_party=first_party_deps,
            third_party=third_party_deps,
            stdlib=stdlib_deps,
        )

        # Note: can only recurse into packages.
        if not recursive or not hasattr(module, "__path__"):
            return grouped_reqs

        # Visit the sub-packages/modules of the package
        # TODO: add dynamically imported submodules using the `pkgutil` module.
        for module_info in pkgutil.walk_packages(module.__path__):
            submodule_name = f"{module.__name__}.{module_info.name}"
            submodule = get_module(submodule_name)
            grouped_reqs |= GroupedRequirements.from_module(submodule)

        return grouped_reqs

    @staticmethod
    def from_file(filepath: Path, /) -> "GroupedRequirements":
        r"""Create grouped requirements from a file."""
        if not filepath.is_file() or not filepath.exists():
            raise FileNotFoundError(f"Invalid file: {filepath}")

        # extract the requirements from the file
        text = filepath.read_text(encoding="utf8")
        tree = ast.parse(text, filename=str(filepath))
        reqs = get_requirements_from_ast(tree)

        first_party_deps: set[Requirement] = set()
        stdlib_deps: set[Requirement] = set()
        third_party_deps: set[Requirement] = set()

        for req in reqs:
            if req.name in STDLIB_MODULES:
                stdlib_deps.add(req)
                continue

            try:
                module_dir = get_requirement_origin(req)
            except ModuleNotFoundError:
                third_party_deps.add(req)
            else:
                if filepath.is_relative_to(module_dir):
                    first_party_deps.add(req)
                else:
                    third_party_deps.add(req)

        return GroupedRequirements(
            first_party=first_party_deps,
            third_party=third_party_deps,
            stdlib=stdlib_deps,
        )

    def __or__(self, other: Self, /) -> "GroupedRequirements":
        return GroupedRequirements(
            first_party=self.first_party | other.first_party,
            third_party=self.third_party | other.third_party,
            stdlib=self.stdlib | other.stdlib,
        )

    def __ior__(self, other: Self, /) -> Self:
        self.first_party |= other.first_party
        self.third_party |= other.third_party
        self.stdlib |= other.stdlib
        return self


def get_name_pyproject(config: dict, /) -> str:
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


def detect_dependencies(filename: str | Path, /) -> GroupedRequirements:
    r"""Collect the dependencies from files in the given path."""
    path = Path(filename)
    grouped_deps: GroupedRequirements = GroupedRequirements()
    if path.is_file():  # Single file
        grouped_deps |= GroupedRequirements.from_file(path)
    elif path.is_dir():  # Directory
        for file_path in path.rglob("*.py"):
            grouped_deps |= detect_dependencies(file_path)
    else:  # assume module
        module_name = path.stem
        module = get_module(module_name)
        grouped_deps |= GroupedRequirements.from_module(module)
    # if not path.exists():
    #     raise FileNotFoundError(f"Invalid path: {path}")

    return grouped_deps


def resolve_dependencies(
    *,
    imported_deps: set[NormalizedName],
    declared_deps: set[NormalizedName],
    excluded_deps: set[NormalizedName],
    excluded_declared_deps: set[NormalizedName],
    excluded_imported_deps: set[NormalizedName],
) -> tuple[set[NormalizedName], set[NormalizedName], set[NormalizedName]]:
    r"""Check the dependencies of a module.

    Args:
        imported_deps: The imported dependencies.
        declared_deps: The declared dependencies.
        excluded_deps: Dependencies to exclude, no matter what.
        excluded_declared_deps: Dependencies to exclude from the declared dependencies.
        excluded_imported_deps: Dependencies to exclude from the imported dependencies.
    """
    # map the imported dependencies to their pip-package names
    actual_deps: set[NormalizedName] = set()
    missing_deps: set[NormalizedName] = set()
    for dep in imported_deps:
        if dep not in PACKAGES:
            missing_deps.add(dep)
            continue

        mapped_deps = get_canonical_names(PACKAGES[dep])
        if len(mapped_deps) != 1:
            raise ValueError(f"Found multiple pip-packages for {dep!r}: {mapped_deps}.")

        actual_deps.add(mapped_deps.pop())

    # canonicalize the names
    excluded_reqs = set(map(canonicalize_name, excluded_deps))
    excluded_imported_reps = set(map(canonicalize_name, excluded_imported_deps))
    excluded_declared_reps = set(map(canonicalize_name, excluded_declared_deps))
    declared_reqs = set(map(canonicalize_name, declared_deps)) - (
        excluded_declared_reps | excluded_reqs
    )
    actual_reps = set(map(canonicalize_name, actual_deps)) - (
        excluded_imported_reps | excluded_reqs
    )
    missing_reps = set(map(canonicalize_name, missing_deps)) - excluded_reqs

    # check if all imported dependencies are listed in pyproject.toml
    undeclared_deps = actual_reps - declared_reqs
    unused_deps = declared_reqs - actual_reps

    return undeclared_deps, unused_deps, missing_reps


def check_file(
    filename: str | Path,
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

    with open(filename, "rb") as file:
        config = tomllib.load(file)

    # get the normalized project name
    project_name: NormalizedName = canonicalize_name(get_name_pyproject(config))
    # get dependencies from pyproject.toml
    declared_deps: set[NormalizedName] = {project_name} | get_canonical_names(
        get_requirements_from_pyproject(config)
    )
    # get test dependencies from pyproject.toml
    declared_test_deps: set[NormalizedName] = {project_name} | get_canonical_names(
        get_dev_requirements_from_pyproject(config, "test")
    )
    # get superfluous test dependencies
    superfluous_test_deps = (declared_deps & declared_test_deps) - {project_name}
    # setup ignored dependencies
    excluded_deps = get_canonical_names(exclude)

    # region check project dependencies ------------------------------------------------
    # detect the imported dependencies from the source files
    detected_deps = detect_dependencies(module_dir)
    imported_deps = get_canonical_names(detected_deps.third_party)
    first_party_deps = get_canonical_names(detected_deps.first_party)
    # get the normalized project name
    undeclared_deps, unused_deps, missing_deps = resolve_dependencies(
        imported_deps=imported_deps,
        declared_deps=declared_deps,
        excluded_deps=excluded_deps,
        excluded_declared_deps=get_canonical_names(known_unused_deps),
        excluded_imported_deps=get_canonical_names(known_undeclared_deps),
    )

    if debug:
        print(
            f"Resolved dependencies:"
            f"\n\tdeclared_deps={sorted(declared_deps)}"
            f"\n\timported_deps={sorted(imported_deps)}"
            f"\n\texcluded_deps={sorted(excluded_deps)}"
            f"\n\tfirst_party_deps={sorted(first_party_deps)}"
            f"\n\tundeclared_deps={sorted(undeclared_deps)}"
            f"\n\tunused_deps={sorted(unused_deps)}"
            f"\n\tmissing_deps={sorted(missing_deps)}"
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
    imported_test_deps = get_canonical_names(detected_test_deps.third_party)
    first_party_test_deps = get_canonical_names(detected_test_deps.first_party)
    # we can safely ignore any undeclared dependencies, if they are part of the declared
    # project dependencies.

    undeclared_test_deps, unused_test_deps, missing_test_deps = resolve_dependencies(
        imported_deps=imported_test_deps,
        declared_deps=declared_test_deps,
        excluded_deps=excluded_deps,
        excluded_declared_deps=get_canonical_names(known_unused_test_deps),
        excluded_imported_deps=declared_deps
        | get_canonical_names(known_undeclared_test_deps),
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
            # debug
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
