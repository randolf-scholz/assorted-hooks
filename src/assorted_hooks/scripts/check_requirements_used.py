#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# ///
# NOTE: illogical type hint in stdlib, maybe open issue.
# https://github.com/python/cpython/blob/608927b01447b110de5094271fbc4d49c60130b0/Lib/importlib/metadata/__init__.py#L933-L947C29
# https://github.com/python/typeshed/blob/d82a8325faf35aa0c9d03d9e9d4a39b7fcb78f8e/stdlib/importlib/metadata/__init__.pyi#L32
r"""Check that declared dependencies are used in the project.

Note:
    Needs to be run as script, since it needs to check

References:
    - https://peps.python.org/pep-0503/
    - https://peps.python.org/pep-0508/
    - https://peps.python.org/pep-0621/
    - https://packaging.python.org/en/latest/specifications/
    - https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#declaring-project-metadata
"""

__all__ = [
    # Constants
    "STDLIB_MODULES",
    "PYPI_NAMES",
    "SILENT",
    "DEBUG",
    "IMPORT_NAMES",
    # Types
    "CanonicalName",
    "ImportName",
    "PypiName",
    # Classes
    "GroupedRequirements",
    "ResolvedDependencies",
    "Requirement",
    # Exceptions
    "InvalidRequirement",
    # Functions
    "canonicalize",
    "check_deps",
    "check_pyproject",
    "detect_dependencies",
    "get_canonical_names",
    "get_dev_requirements_from_pyproject",
    "get_import_names",
    "get_module_path",
    "get_module",
    "get_name_pyproject",
    "get_packages",
    "get_packages_inverse",
    "get_pypi_names",
    "get_requirement_origin",
    "get_requirements_from_ast",
    "get_requirements_from_module",
    "get_requirements_from_pyproject",
    "main",
    "resolve_dependencies",
    "yield_deps",
    "yield_dev_deps",
    "yield_imports",
]

import argparse
import ast
import importlib
import os
import pkgutil
import re
import sys
import tomllib
import warnings
from ast import Import, ImportFrom
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence, Set as AbstractSet
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from functools import cache
from importlib import metadata
from importlib.util import find_spec
from pathlib import Path
from re import Pattern
from types import ModuleType
from typing import Any, NamedTuple, NewType, Optional, Self, cast

# region pypa.packaging ----------------------------------------------------------------
# NOTE: Manual implementation instead of pypa.packaging to avoid dependency.
CanonicalName = NewType("CanonicalName", str)
r"""A type hint for normalized names."""
ImportName = NewType("ImportName", CanonicalName)
r"""A type hint for PyPI package names."""
PypiName = NewType("PypiName", CanonicalName)
r"""A type hint for PyPI package names."""


def canonicalize(name: str, /) -> CanonicalName:
    r"""Normalize the name of a package (PEP 503)."""
    normalized = re.sub(r"[-_.]+", "-", name).lower()
    return cast("CanonicalName", normalized)


def get_packages() -> dict[ImportName, frozenset[PypiName]]:
    r"""Get the mapping of module names to their pip-package names."""
    d: dict[ImportName, frozenset[PypiName]] = {}
    for key, vals in metadata.packages_distributions().items():
        if not vals:
            raise ValueError(f"Found empty list of distributions for {key!r}.")

        canonical_key = cast("ImportName", canonicalize(key))
        canonical_vals = frozenset(cast("PypiName", canonicalize(v)) for v in vals)
        d[canonical_key] = canonical_vals
    return d


def get_packages_inverse() -> dict[PypiName, frozenset[ImportName]]:
    r"""Get the mapping of pip-package names to their module names."""
    d: dict[PypiName, set[ImportName]] = defaultdict(set)
    for key, vals in metadata.packages_distributions().items():
        canonical_key = cast("ImportName", canonicalize(key))
        for val in vals:
            canonical_value = cast("PypiName", canonicalize(val))
            d[canonical_value].add(canonical_key)
    # convert to frozenset
    return {k: frozenset(v) for k, v in d.items()}


class InvalidRequirement(ValueError):  # noqa: N818
    r"""An invalid requirement was found, users should refer to PEP 508."""


class Requirement:
    r"""Parse a requirement string like 'foo>=1.0' into its parts.

    We are only interested in the name here.

    References:
        - https://www.python.org/dev/peps/pep-0508/
        - https://packaging.pypa.io/en/latest/specifications/core-metadata/
    """

    NAME_PATTERN = re.compile(
        r"\b(?P<name>[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?)\b"
    )
    name: str

    def __init__(self, spec: str, /) -> None:
        if match := self.NAME_PATTERN.match(spec):
            self.name = match.group("name")
        else:
            raise InvalidRequirement(f"Invalid requirement: {spec!r}")


def get_canonical_names(
    reqs: Iterable[str | Requirement], /
) -> frozenset[CanonicalName]:
    r"""Get the canonical names from a list of requirements."""
    return frozenset(canonicalize(r if isinstance(r, str) else r.name) for r in reqs)


def get_import_names(reqs: Iterable[str | Requirement], /) -> frozenset[ImportName]:
    r"""Get the canonical names from a list of requirements."""
    return frozenset(
        ImportName(canonicalize(r if isinstance(r, str) else r.name)) for r in reqs
    )


def get_pypi_names(reqs: Iterable[str | Requirement], /) -> frozenset[PypiName]:
    r"""Get the canonical names from a list of requirements."""
    return frozenset(
        PypiName(canonicalize(r if isinstance(r, str) else r.name)) for r in reqs
    )


# endregion pypa.packaging -------------------------------------------------------------

# region constants ---------------------------------------------------------------------
STDLIB_MODULES: frozenset[CanonicalName] = frozenset(
    map(canonicalize, sys.stdlib_module_names)
)
r"""A set of all standard library modules."""
PYPI_NAMES: dict[ImportName, frozenset[PypiName]] = get_packages()
r"""A dictionary that maps module names to their pip-package names."""
IMPORT_NAMES: dict[PypiName, frozenset[ImportName]] = get_packages_inverse()
r"""A dictionary that maps pip-package names to their module names."""
SILENT: bool = True
r"""Global flag to suppress output."""
DEBUG: bool = False
r"""Global flag to print debug information."""
# endregion constants ------------------------------------------------------------------


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
    - `tool.poety.group.*.dependencies`
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


def detect_dependencies(
    filename: str | Path, /, *, excluded: AbstractSet[str]
) -> GroupedRequirements:
    r"""Collect the dependencies from files in the given path."""
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Invalid path: {path}")

    grouped_deps: GroupedRequirements = GroupedRequirements()

    # skip if any part of the path is excluded
    if any(part in excluded for part in path.parts):
        return grouped_deps

    if path.is_file():  # Single file
        grouped_deps |= GroupedRequirements.from_file(path)
    elif path.is_dir():  # Directory
        for file_path in path.rglob("*.py"):
            grouped_deps |= detect_dependencies(file_path, excluded=excluded)
    else:  # assume module
        module_name = path.stem
        module = get_module(module_name)
        grouped_deps |= GroupedRequirements.from_module(module)

    return grouped_deps


class ResolvedDependencies(NamedTuple):
    r"""A named tuple containing the resolved dependencies."""

    undeclared_deps: AbstractSet[ImportName]
    r"""Dependencies that are imported but not declared."""
    unimported_deps: AbstractSet[PypiName]
    r"""Dependencies that are declared but not imported."""
    imported_unknown: AbstractSet[ImportName]
    r"""Dependencies that are imported but not recognized."""
    declared_unknown: AbstractSet[PypiName]
    r"""Dependencies that are declared but not recognized."""


def resolve_dependencies(
    *,
    # Note: use frozenset to ensure immutability.
    imported_deps: frozenset[ImportName],
    declared_deps: frozenset[PypiName],
    excluded_deps: frozenset[Any],
    local_deps: frozenset[Any],
    known_unimported_deps: frozenset[PypiName],  # PyPIName
    known_undeclared_deps: frozenset[ImportName],  # ImportName
) -> ResolvedDependencies:
    r"""Check the dependencies of a module.

    Args:
        imported_deps: The imported dependencies.
        declared_deps: The declared dependencies.
        excluded_deps: Dependencies to exclude, no matter what.
        local_deps: The local dependencies.
        known_unimported_deps: Dependencies to exclude from the declared dependencies.
        known_undeclared_deps: Dependencies to exclude from the imported dependencies.
    """
    if DEBUG:
        print(
            f"\nResolving:"
            f"\n\timported_deps={sorted(imported_deps)}"
            f"\n\tdeclared_deps={sorted(declared_deps)}"
            f"\n\texcluded_deps={sorted(excluded_deps)}"
            f"\n\tlocal_deps={sorted(local_deps)}"
            f"\n\tknown_unimported_deps={sorted(known_unimported_deps)}"
            f"\n\tknown_undeclared_deps={sorted(known_undeclared_deps)}"
        )

    # parse the exclusions
    imported_excluded: set[ImportName] = (
        {dep for dep in excluded_deps if dep in PYPI_NAMES}
        | {x for dep in excluded_deps for x in IMPORT_NAMES.get(dep, ())}
        | {dep for dep in known_undeclared_deps if dep in PYPI_NAMES}
        | {x for dep in known_undeclared_deps for x in IMPORT_NAMES.get(dep, ())}  # type: ignore[call-overload]
    )
    declared_excluded: set[PypiName] = (
        {dep for dep in excluded_deps if dep in IMPORT_NAMES}
        | {x for dep in excluded_deps for x in PYPI_NAMES.get(dep, ())}
        | {dep for dep in known_unimported_deps if dep in IMPORT_NAMES}
        | {x for dep in known_unimported_deps for x in PYPI_NAMES.get(dep, ())}  # type: ignore[call-overload]
    )
    # map the imported dependencies to their pip-package names
    declared: frozenset[PypiName] = declared_deps - declared_excluded
    imported: frozenset[ImportName] = imported_deps - imported_excluded
    local: frozenset[Any] = local_deps

    imported_known = imported & PYPI_NAMES.keys()
    declared_known = declared & IMPORT_NAMES.keys()

    imported_unknown = imported - (imported_known | local)
    declared_unknown = declared - (declared_known | local)

    # NOTE: one name can have multiple results, as multiple PyPI packages can map to the same module.
    pypi_names_of_imported = {x for dep in imported_known for x in PYPI_NAMES[dep]}
    import_names_of_declared = {x for dep in declared_known for x in IMPORT_NAMES[dep]}

    undeclared_deps = imported - (
        import_names_of_declared | imported_excluded | local_deps
    )
    unimported_deps = declared - (
        pypi_names_of_imported | declared_excluded | local_deps
    )

    if DEBUG:
        print(
            f"\nResolved dependencies:"
            f"\n\tlocal:                   {sorted(local)}"
            "\n\t---------------------------"
            f"\n\timported:                {sorted(imported)}"
            f"\n\timported and known:      {sorted(imported_known)}"
            f"\n\timported and excluded:   {sorted(imported_excluded)}"
            f"\n\tdeclared packages:       {sorted(import_names_of_declared)}"
            "\n\t---------------------------"
            f"\n\tdeclared:                {sorted(declared)}"
            f"\n\tdeclared and known:      {sorted(declared_known)}"
            f"\n\tdeclared and excluded:   {sorted(declared_excluded)}"
            f"\n\timported packages:       {sorted(pypi_names_of_imported)}"
            "\n\t---------------------------"
            f"\n\timported but undeclared: {sorted(undeclared_deps)}"
            f"\n\tdeclared but unimported: {sorted(unimported_deps)}"
            f"\n\tdeclared but unknown:    {sorted(declared_unknown)}"
            f"\n\timported but unknown:    {sorted(imported_unknown)}"
        )

    return ResolvedDependencies(
        undeclared_deps=undeclared_deps,
        unimported_deps=unimported_deps,
        imported_unknown=imported_unknown,
        declared_unknown=declared_unknown,
    )


def check_deps(
    *,
    declared_deps: frozenset[PypiName],
    imported_deps: frozenset[ImportName],
    excluded_deps: frozenset[CanonicalName],
    local_deps: frozenset[CanonicalName],
    known_unimported_deps: frozenset[PypiName],
    known_undeclared_deps: frozenset[ImportName],
    # flags
    error_on_undeclared_deps: bool = True,
    error_on_unimported_deps: bool = True,
    error_on_unknown_imports: bool = True,
    error_on_unknown_declars: bool = True,
) -> int:
    r"""Check the dependencies of a module."""
    resolved_deps = resolve_dependencies(
        declared_deps=declared_deps,
        imported_deps=imported_deps,
        excluded_deps=excluded_deps,
        local_deps=local_deps,
        known_undeclared_deps=known_undeclared_deps,
        known_unimported_deps=known_unimported_deps,
    )
    undeclared_deps = resolved_deps.undeclared_deps
    unimported_deps = resolved_deps.unimported_deps
    unknown_imports = resolved_deps.imported_unknown
    unknown_declars = resolved_deps.declared_unknown

    violations = 0

    if undeclared_deps and error_on_undeclared_deps:
        violations += 1
        print(f"Detected undeclared dependencies: {undeclared_deps}")
    if unimported_deps and error_on_unimported_deps:
        violations += 1
        print(f"Detected unused dependencies: {unimported_deps}")
    if unknown_imports and error_on_unknown_imports:
        violations += 1
        print(f"Detected unknown imports: {unknown_imports}")
    if unknown_declars and error_on_unknown_declars:
        violations += 1
        print(f"Detected unknown declarations: {unknown_declars}")

    return violations
    # endregion check project dependencies ---------------------------------------------


def check_pyproject(
    pyproject_file: str | Path,
    /,
    *,
    module_dir: str = "src/",
    tests_dir: Optional[str] = "tests/",
    exclude: Sequence[str] = (),
    known_unimported: Sequence[str] = (),
    known_unimported_test: Sequence[str] = (),
    known_undeclared: Sequence[str] = (),
    known_undeclared_test: Sequence[str] = (),
    error_on_superfluous_test_deps: bool = True,
    error_on_undeclared_deps: bool = True,
    error_on_undeclared_test_deps: bool = True,
    error_on_unimported_deps: bool = True,
    error_on_unimported_test_deps: bool = False,
    error_on_unknown_imports: bool = True,
    error_on_unknown_declars: bool = True,
    error_on_unknown_test_imports: bool = True,
    error_on_unknown_test_declars: bool = True,
) -> int:
    r"""Check a single file."""
    violations: int
    if not Path(module_dir).is_dir():
        raise FileNotFoundError(f"{module_dir} is not a directory.")
    if not (tests_dir is None or Path(tests_dir).is_dir()):
        raise FileNotFoundError(f"{tests_dir} is not a directory.")

    with open(pyproject_file, "rb") as file:
        config = tomllib.load(file)

    # get the normalized project name
    project_name: Any = canonicalize(get_name_pyproject(config))
    testdir_name: Any = canonicalize(Path(tests_dir).stem) if tests_dir else None

    excluded_deps = get_canonical_names(exclude)
    excluded_subdirs = set() if testdir_name is None else {testdir_name}

    # check project dependencies -------------------------------------------------------
    if DEBUG:
        print(f"----- Checking MODULE DIR {module_dir} -----")

    main_requirements = get_requirements_from_pyproject(config)
    detected_deps = detect_dependencies(module_dir, excluded=excluded_subdirs)
    declared_deps = get_pypi_names(main_requirements)
    imported_deps = get_import_names(detected_deps.third_party)
    local_deps = frozenset({project_name})
    known_unimported_deps = get_pypi_names(known_unimported)
    known_undeclared_deps = get_import_names(known_undeclared)

    violations = check_deps(
        imported_deps=imported_deps,
        declared_deps=declared_deps,
        excluded_deps=excluded_deps,
        local_deps=local_deps,
        known_unimported_deps=known_unimported_deps,
        known_undeclared_deps=known_undeclared_deps,
        # flags
        error_on_undeclared_deps=error_on_undeclared_deps,
        error_on_unimported_deps=error_on_unimported_deps,
        error_on_unknown_imports=error_on_unknown_imports,
        error_on_unknown_declars=error_on_unknown_declars,
    )

    # check test dependencies ----------------------------------------------------------
    if tests_dir is None:
        return violations

    if DEBUG:
        print(f"----- Checking TEST DIR {testdir_name} -----")

    test_requirements = get_dev_requirements_from_pyproject(config, "test")
    detected_test_deps = detect_dependencies(tests_dir, excluded=set())
    imported_test_deps = get_import_names(detected_test_deps.third_party)
    declared_test_deps = get_pypi_names(test_requirements)
    local_test_deps = frozenset({testdir_name})
    known_unimported_test_deps = get_pypi_names(known_unimported_test)
    known_undeclared_test_deps = get_import_names(known_undeclared_test)

    # check for superfluous test dependencies
    superfluous_test_deps = (declared_test_deps & declared_deps) - {project_name}
    if superfluous_test_deps and error_on_superfluous_test_deps:
        violations += 1
        print(f"Detected superfluous dependencies: {sorted(superfluous_test_deps)}")

    violations += check_deps(
        imported_deps=imported_test_deps | imported_deps,  # use both
        declared_deps=declared_test_deps | declared_deps,  # use both
        excluded_deps=excluded_deps,
        local_deps=local_test_deps | local_deps,  # use both
        known_unimported_deps=known_unimported_test_deps | known_unimported_deps,
        known_undeclared_deps=known_undeclared_test_deps | known_undeclared_deps,
        # flags
        error_on_undeclared_deps=error_on_undeclared_test_deps,
        error_on_unimported_deps=error_on_unimported_test_deps,
        error_on_unknown_imports=error_on_unknown_test_imports,
        error_on_unknown_declars=error_on_unknown_test_declars,
    )

    return violations


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
        "--known-unimported",
        default=[],
        nargs="*",
        type=str,
        help="List of used project dependencies to ignore.",
    )
    parser.add_argument(
        "--known-unimported-test",
        default=[],
        nargs="*",
        type=str,
        help="List of used test dependencies to ignore.",
    )
    parser.add_argument(
        "--known-undeclared",
        default=[],
        nargs="*",
        type=str,
        help="List of undeclared project dependencies to ignore.",
    )
    parser.add_argument(
        "--known-undeclared-test",
        default=[],
        nargs="*",
        type=str,
        help="List of undeclared test dependencies to ignore.",
    )
    # flags ----------------------------------------------------------------------------
    parser.add_argument(
        "--error-on-undeclared-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if project dependency is undeclared.",
    )
    parser.add_argument(
        "--error-on-undeclared-test-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if test dependency is undeclared.",
    )
    parser.add_argument(
        "--error-on-unimported-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if project dependency is unused.",
    )
    parser.add_argument(
        "--error-on-unimported-test-deps",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Raise error if test dependency is unused.",
    )
    parser.add_argument(
        "--error-on-unknown-imports",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if imported project dependency is missing (not installed).",
    )
    parser.add_argument(
        "--error-on-unknown-test-imports",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if imported test dependency is missing (not installed).",
    )
    parser.add_argument(
        "--error-on-unknown-declars",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if declared project dependency is missing (not installed).",
    )
    parser.add_argument(
        "--error-on-unknown-test-declars",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if declared test dependency is not missing (not installed).",
    )
    # other
    parser.add_argument(
        "--error-on-superfluous-test-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if test dependency is superfluous.",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Print debug information.",
    )
    parser.add_argument(
        "--silent",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Load modules silently.",
    )
    args = parser.parse_args()

    global DEBUG, SILENT  # noqa: PLW0603
    SILENT = args.silent
    DEBUG = args.debug

    try:
        violations = check_pyproject(
            args.pyproject_file,
            module_dir=args.module_dir,
            tests_dir=args.tests_dir,
            exclude=args.exclude,
            known_unimported=args.known_unimported,
            known_unimported_test=args.known_unimported_test,
            known_undeclared=args.known_undeclared,
            known_undeclared_test=args.known_undeclared_test,
            # error selection
            error_on_unimported_deps=args.error_on_unimported_deps,
            error_on_unimported_test_deps=args.error_on_unimported_test_deps,
            error_on_undeclared_deps=args.error_on_undeclared_deps,
            error_on_undeclared_test_deps=args.error_on_undeclared_test_deps,
            error_on_unknown_imports=args.error_on_unknown_imports,
            error_on_unknown_declars=args.error_on_unknown_declars,
            error_on_unknown_test_imports=args.error_on_unknown_test_imports,
            error_on_unknown_test_declars=args.error_on_unknown_test_declars,
            # debug
            error_on_superfluous_test_deps=args.error_on_superfluous_test_deps,
        )
    except Exception as exc:
        exc.add_note(f"Checking file {args.pyproject_file!s} failed!")
        raise

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
