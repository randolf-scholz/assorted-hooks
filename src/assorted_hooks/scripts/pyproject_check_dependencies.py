#!/usr/bin/env python
"""Prints the direct dependencies of a module line by line.

References:
    - https://peps.python.org/pep-0508/
    - https://peps.python.org/pep-0621/
    - https://packaging.python.org/en/latest/specifications/
    - https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#declaring-project-metadata
"""

# TODO: add support for extras.

__all__ = [
    "collect_dependencies",
    "get_deps_file",
    "get_deps_import",
    "get_deps_importfrom",
    "get_deps_module",
    "get_deps_pyproject_project",
    "get_deps_pyproject_section",
    "get_deps_pyproject_tests",
    "get_deps_tree",
    "get_name_pyproject",
    "group_dependencies",
    "main",
    "normalize_dep_name",
]

import argparse
import ast
import importlib
import pkgutil
import re
import sys
from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple, TypeAlias

Config: TypeAlias = dict[str, Any]

MODULES_DEFAULT = ("src/",)
TESTS_DEFAULT = ("tests/",)

# https://peps.python.org/pep-0508/#names
# NOTE: we modify this regex a bit to allow to match inside context
RE_NAME = re.compile(r"""\b[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?\b""")
NAME = RE_NAME.pattern
RE_NAME_GROUP = re.compile(rf"""(?P<name>{NAME})""")
NAME_GROUP = RE_NAME_GROUP.pattern
assert RE_NAME_GROUP.groups == 1, f"{RE_NAME_GROUP.groups=}."


# import metadata library
for name in (
    ["importlib.metadata", "importlib_metadata"]
    if sys.version_info >= (3, 11)
    else ["importlib_metadata"]
):
    # NOTE: importlib.metadata is bugged in 3.10: https://github.com/python/cpython/issues/94113
    try:
        metadata = importlib.import_module(name)
        break
    except ImportError:
        pass
else:
    raise ImportError(
        "This pre-commit hook runs in the local interpreter and requires importlib.metadata!"
        " Please use python≥3.11 or install 'importlib_metadata'."
    )

# import toml library
for name in ("tomllib", "tomlkit", "tomli"):
    try:
        tomllib = importlib.import_module(name)
        break
    except ImportError:
        pass
else:
    raise ImportError(
        "This pre-commit hook runs in the local interpreter and requires a suitable TOML-library!"
        " Please use python≥3.11 or install one of 'tomlkit' or 'tomli'."
    )

PACKAGES: dict[str, list[str]] = metadata.packages_distributions()
"""A dictionary that maps module names to their pip-package names."""

# NOTE: illogical type hint in stdlib, maybe open issue.
# https://github.com/python/cpython/blob/608927b01447b110de5094271fbc4d49c60130b0/Lib/importlib/metadata/__init__.py#L933-L947C29
# https://github.com/python/typeshed/blob/d82a8325faf35aa0c9d03d9e9d4a39b7fcb78f8e/stdlib/importlib/metadata/__init__.pyi#L32


def normalize_dep_name(dep: str, /) -> str:
    """Normalize a dependency name."""
    return dep.lower().replace("-", "_")


def get_deps_import(node: ast.Import, /) -> set[str]:
    """Extract dependencies from an `import ...` statement."""
    dependencies = set()
    for alias in node.names:
        module = alias.name.split(".")[0]
        if not module.startswith("_"):
            dependencies.add(module)
    return dependencies


def get_deps_importfrom(node: ast.ImportFrom, /) -> set[str]:
    """Extract dependencies from an `from y import ...` statement."""
    assert node.module is not None
    module_name = node.module.split(".")[0]
    if module_name.startswith("_"):  # ignore _private modules
        return set()
    return {module_name}


def get_deps_tree(tree: ast.AST, /) -> set[str]:
    """Extract the set of dependencies from `ast.AST` object."""
    dependencies: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dependencies |= get_deps_import(node)
        elif isinstance(node, ast.ImportFrom):
            dependencies |= get_deps_importfrom(node)

    return dependencies


def get_deps_file(file_path: str | Path, /) -> set[str]:
    """Extract set of dependencies imported by a script."""
    path = Path(file_path)

    if path.suffix != ".py":
        raise ValueError(f"Invalid file extension: {path.suffix}")

    with open(path, "r", encoding="utf8") as file:
        tree = ast.parse(file.read())

    return get_deps_tree(tree)


def get_deps_module(module: str | ModuleType, /, *, silent: bool = True) -> set[str]:
    """Extract set of dependencies imported by a module."""
    # NOTE: Generally there is no correct way to do it without importing the module.
    # This is because modules can be imported dynamically.

    if isinstance(module, str):
        with (  # load the submodule silently
            redirect_stdout(None if silent else sys.stdout),
            redirect_stderr(None if silent else sys.stderr),
        ):
            module = importlib.import_module(module)

    # Visit the current module
    assert module.__file__ is not None
    dependencies = get_deps_file(module.__file__)

    if not hasattr(module, "__path__"):
        # note: can only recurse into packages.
        return dependencies

    # Visit the sub-packages/modules of the package
    # TODO: add dynamically imported submodules using the `pkgutil` module.
    for module_info in pkgutil.walk_packages(module.__path__):
        submodule_name = f"{module.__name__}.{module_info.name}"
        dependencies |= get_deps_module(submodule_name, silent=silent)

    return dependencies


def get_name_pyproject(config: Config, /) -> str:
    """Get the name of the project from pyproject.toml."""
    try:
        project_name = config["project"]["name"]
    except KeyError:
        project_name = NotImplemented
    try:
        poetry_name = config["tool"]["poetry"]["name"]
    except KeyError:
        poetry_name = NotImplemented

    match project_name, poetry_name:
        case str() as a, str() as b:
            if a != b:
                raise ValueError(
                    "Found inconsistent project names in [project] and [tool.poetry]."
                    f"\n [project]     is missing: {a}, "
                    f"\n [tool.poetry] is missing: {b}."
                )
            return a
        case str() as a, _:
            return a
        case _, str() as b:
            return b
        case _:
            raise ValueError("No project name found in [project] or [tool.poetry].")


def get_deps_pyproject_section(config: Config, /, *, section: str) -> set[str]:
    """Get the dependencies from a section of pyproject.toml.

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
        case list() as lst:
            matches: set[str] = set()
            for dep in lst:
                match = re.search(RE_NAME, dep)
                if match is None:
                    raise ValueError(f"Invalid dependency: {dep!r}")
                matches.add(match.group())
            return matches
        # assume format `package = "<comparator>version"`
        case dict() as dct:  # poetry
            return set(dct.keys()) - {"python"}
        case _:
            raise TypeError(f"Unexpected type: {type(config)}")


def get_deps_pyproject_project(config: Config, /) -> set[str]:
    """Extract the dependencies from a pyproject.toml file.

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
        case set() as a, set() as b:
            if (left := a - b) | (right := b - a):
                raise ValueError(
                    "Found inconsistent dependencies in [project] and [tool.poetry]."
                    f"\n [project]     is missing: {right}, "
                    f"\n [tool.poetry] is missing: {left}."
                )
            project_dependencies = a
        case set() as a, _:
            project_dependencies = a
        case _, set() as b:
            project_dependencies = b
        case _:
            project_dependencies = set()

    return project_dependencies


def get_deps_pyproject_tests(config: Config, /) -> set[str]:
    """Extract the test dependencies from a pyproject.toml file."""
    dependencies = {
        key: get_deps_pyproject_section(config, section=key)
        for key in (
            "project.optional-dependencies.test",
            "project.optional-dependencies.tests",
            "tool.poetry.group.test.dependencies",
            "tool.poetry.group.tests.dependencies",
        )
    }

    match (
        dependencies["project.optional-dependencies.test"],
        dependencies["project.optional-dependencies.tests"],
    ):
        case set(), set():
            raise ValueError(
                "Found both [project.optional-dependencies.test]"
                " and [project.optional-dependencies.tests]."
            )
        case set() as a, _:
            project_test_dependencies = a
        case _, set() as b:
            project_test_dependencies = b
        case _:
            project_test_dependencies = NotImplemented

    match (
        dependencies["tool.poetry.group.test.dependencies"],
        dependencies["tool.poetry.group.tests.dependencies"],
    ):
        case set(), set():
            raise ValueError(
                "Found both [tool.poetry.group.test.dependencies]"
                " and [tool.poetry.group.tests.dependencies]."
            )
        case set() as a, _:
            poetry_test_dependencies = a
        case _, set() as b:
            poetry_test_dependencies = b
        case _:
            poetry_test_dependencies = NotImplemented

    match (
        project_test_dependencies,
        poetry_test_dependencies,
    ):
        case set() as a, set() as b:
            if (left := a - b) | (right := b - a):
                raise ValueError(
                    "Found different test dependencies in [project] and [tool.poetry]."
                    f"\n [project]     is missing: {right}, "
                    f"\n [tool.poetry] is missing: {left}."
                )
            test_dependencies = a
        case set() as a, _:
            test_dependencies = a
        case _, set() as b:
            test_dependencies = b
        case _:
            test_dependencies = set()

    return test_dependencies


class GroupedDependencies(NamedTuple):
    """A named tuple containing the dependencies grouped by type."""

    imported_dependencies: set[str]
    stdlib_dependencies: set[str]


def group_dependencies(dependencies: set[str], /) -> GroupedDependencies:
    """Splits the dependencies into first-party and third-party."""
    imported_dependencies = set()
    stdlib_dependencies = set()

    for dependency in dependencies:
        if dependency in sys.stdlib_module_names:
            stdlib_dependencies.add(dependency)
        else:
            imported_dependencies.add(dependency)

    return GroupedDependencies(
        imported_dependencies=imported_dependencies,
        stdlib_dependencies=stdlib_dependencies,
    )


def collect_dependencies(
    fname: str | Path, /, *, raise_notfound: bool = True
) -> set[str]:
    """Collect the third-party dependencies from files in the given path."""
    path = Path(fname)
    dependencies = set()

    if path.is_file():  # Single file
        dependencies |= get_deps_file(path)
    elif path.is_dir():  # Directory
        for file_path in path.rglob("*.py"):
            if file_path.is_file():
                dependencies |= get_deps_file(file_path)
    elif not path.exists():  # assume module
        try:
            dependencies |= get_deps_module(str(fname))
        except ModuleNotFoundError as exc:
            if raise_notfound:
                raise exc
    elif raise_notfound:
        raise FileNotFoundError(f"Invalid path: {path}")

    return dependencies


def validate_dependencies(
    *,
    pyproject_dependencies: set[str],
    imported_dependencies: set[str],
) -> tuple[set[str], set[str], set[str]]:
    """Validate the dependencies."""
    # extract 3rd party dependencies.
    imported_dependencies = group_dependencies(
        imported_dependencies
    ).imported_dependencies

    # map the dependencies to their pip-package names
    imported_deps: set[str] = set()
    unknown_deps: set[str] = set()
    for dep in imported_dependencies:
        if dep not in PACKAGES:
            unknown_deps.add(dep)
            continue

        # get the pypi-package name
        values: list[str] = PACKAGES[dep]
        if len(values) > 1:
            raise ValueError(f"Found multiple pip-packages for {dep!r}: {values}.")
        imported_deps.add(values[0])

    # normalize the dependencies
    pyproject_deps = {normalize_dep_name(dep) for dep in pyproject_dependencies}
    imported_deps = {normalize_dep_name(dep) for dep in imported_deps}

    # check if all imported dependencies are listed in pyproject.toml
    missing_deps = imported_deps - pyproject_deps
    unused_deps = pyproject_deps - imported_deps

    return missing_deps, unused_deps, unknown_deps


def check_file(
    fname: str | Path,
    /,
    *,
    modules: Sequence[str] = MODULES_DEFAULT,
    tests: Sequence[str] = TESTS_DEFAULT,
    ignore_imported_deps: Sequence[str] = (),
    ignore_project_deps: Sequence[str] = (),
    ignore_test_deps: Sequence[str] = (),
    error_superfluous_test_deps: bool = True,
    error_unused_project_deps: bool = True,
    error_unused_test_deps: bool = False,
    debug: bool = False,
) -> bool:
    """Check a single file."""
    passed = True

    with open(fname, "rb") as file:
        config = tomllib.load(file)

    # get the normalized project name
    project_name = normalize_dep_name(get_name_pyproject(config))

    if debug:
        print(f"{project_name=}")

    excluded_dependencies = {project_name} | set(ignore_imported_deps)
    # compute the dependencies from the source files
    modules_given = modules is not MODULES_DEFAULT
    imported_dependencies = set().union(
        *(
            collect_dependencies(fname, raise_notfound=modules_given)
            for fname in modules
        )
    )
    # ignore the excluded dependencies
    imported_dependencies -= excluded_dependencies
    # get dependencies from pyproject.toml
    pyproject_dependencies = get_deps_pyproject_project(config)
    # remove ignored dependencies
    pyproject_dependencies -= set(ignore_project_deps)
    # validate the dependencies
    missing_deps, unused_deps, unknown_deps = validate_dependencies(
        pyproject_dependencies=pyproject_dependencies,
        imported_dependencies=imported_dependencies,
    )
    if missing_deps or unknown_deps or (unused_deps and error_unused_project_deps):
        passed = False
        print(
            f"Found discrepancy between imported dependencies and pyproject.toml!"
            f"\nImported dependencies not listed in pyproject.toml: {missing_deps}."
            f"\nUnused dependencies listed in pyproject.toml: {unused_deps}."
            f"\nUnknown dependencies: {unknown_deps}."
            f"\n"
            f"\nNOTE: Optional dependencies are currently not supported (PR welcome)."
            f"\nNOTE: Workaround: use `importlib.import_module('optional_dependency')`."
        )

    # ---------------------------------------------------------------------------------------------

    # compute the test dependencies from the test files
    excluded_dependencies |= imported_dependencies
    tests_given = tests is not TESTS_DEFAULT
    imported_test_dependencies = set().union(
        *(collect_dependencies(fname, raise_notfound=tests_given) for fname in tests)
    )
    # ignore the excluded dependencies
    imported_test_dependencies -= excluded_dependencies
    # get dependencies from pyproject.toml
    pyproject_test_dependencies = get_deps_pyproject_tests(config)
    # remove ignored dependencies
    pyproject_test_dependencies -= set(ignore_test_deps)
    # validate the dependencies
    missing_test_deps, unused_test_deps, unknown_test_deps = validate_dependencies(
        pyproject_dependencies=pyproject_test_dependencies,
        imported_dependencies=imported_test_dependencies,
    )

    if (
        superfluous_test_deps := imported_dependencies & pyproject_test_dependencies
    ) and error_superfluous_test_deps:
        passed = False
        print(
            f"Found superfluous test dependencies!"
            f"\nSuperfluous test dependencies: {superfluous_test_deps}."
            f"\nAre not needed since they are already listed in [project] or [tool.poetry.dependencies]."
        )
    if (
        missing_test_deps
        or unknown_test_deps
        or (unused_test_deps and error_unused_test_deps)
    ):
        passed = False
        print(
            f"Found discrepancy between imported test dependencies and pyproject.toml!"
            f"\nImported test dependencies not listed in pyproject.toml: {missing_test_deps}."
            f"\nUnused test dependencies listed in pyproject.toml: {unused_test_deps}."
            f"\nUnknown test dependencies: {unknown_test_deps}."
            f"\n"
            f"\nNOTE: Optional dependencies are currently not supported (PR welcome)."
            f"\nNOTE: Workaround: use `importlib.import_module('optional_dependency')`."
        )
    return passed


def main() -> None:
    """Print the third-party dependencies of a module."""
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
        "--modules",
        nargs="*",
        default=MODULES_DEFAULT,
        type=str,
        help="The folder of the module to check.",
    )
    parser.add_argument(
        "--tests",
        nargs="*",
        default=TESTS_DEFAULT,
        type=str,
        help="The path to the test directories.",
    )
    parser.add_argument(
        "--ignore-imported-deps",
        default=[],
        nargs="*",
        type=str,
        help="list of import dependencies to ignore",
    )
    parser.add_argument(
        "--ignore-project-deps",
        default=[],
        nargs="*",
        type=str,
        help="list of pyproject dependencies to ignore.",
    )
    parser.add_argument(
        "--ignore-test-deps",
        default=[],
        nargs="*",
        type=str,
        help="list of pyproject test dependencies to ignore",
    )
    parser.add_argument(
        "--error-superfluous-test-deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if test dependency is superfluous.",
    )
    parser.add_argument(
        "--error_unused_project_deps",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Raise error if pyproject.toml lists unused project dependencies",
    )
    parser.add_argument(
        "--error_unused_test_deps",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Raise error if pyproject.toml lists unused test dependencies",
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
        passed = check_file(
            args.pyproject_file,
            modules=args.modules,
            tests=args.tests,
            ignore_imported_deps=args.ignore_imported_deps,
            ignore_project_deps=args.ignore_project_deps,
            ignore_test_deps=args.ignore_test_deps,
            error_superfluous_test_deps=args.error_superfluous_test_deps,
            error_unused_project_deps=args.error_unused_project_deps,
            error_unused_test_deps=args.error_unused_test_deps,
            debug=args.debug,
        )
    except Exception as exc:
        raise RuntimeError(f'Checking file "{args.pyproject_file!s}" failed!') from exc

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
