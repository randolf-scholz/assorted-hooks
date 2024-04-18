#!/usr/bin/env python
r"""Check for clean interface.

By this, we mean that when a module is imported the `dir(mymodule)` should contain
only things listed in `mymodule.__all__`, with a few exceptions for convenience.
More specifically, usually a module contains a few pre-defined variables, such as

    >>> dir()
    ['__annotations__', '__builtins__', '__doc__', '__loader__', '__name__', '__package__', '__spec__']

For this purpose, we use the following defaults:

- `--check-modules`: True
- `--check-packages`: True
- `--check-private`: False
- `--ignore-imports-modules`: True
- `--ignore-imports-packages`: False
- `--ignore-dunder-attributes`: True
- `--ignore-private-attributes`: True

That is, by default we check all modules and packages,
but ignore private modules and attributes, as well as dunder and private attributes.
Moreover, we are more lenient within modules by ignoring imported variables.
To satisfy this check, global variables that are not listed in `__all__`
should be made private or added to `__all__`.
"""

__all__ = [
    "check_file",
    "check_module",
    "get_imported_names",
    "get_python_files",
    "get_type_aliases",
    "get_type_variables",
    "is_dunder",
    "is_module",
    "is_package",
    "is_private",
    "load_module",
    "main",
]

import argparse
import ast
import logging
import sys
from ast import AST, AnnAssign, Assign, Call, Import, ImportFrom, Name
from collections.abc import Iterable
from contextlib import redirect_stderr, redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Optional

__logger__ = logging.getLogger(__name__)


def get_imported_names(tree: AST, /) -> set[str]:
    r"""Get all imports from AST."""
    imported_symbols: set[str] = set()

    for node in ast.walk(tree):
        match node:
            case Import(names=imports) | ImportFrom(names=imports):
                imported_symbols.update(alias.asname or alias.name for alias in imports)

    return imported_symbols


def get_type_variables(tree: AST, /) -> set[str]:
    r"""Get all type variables from AST (also included `ParamSpec` and `TypeVarTuple`).

    Example: If `U = TypeVar("U", **options)`, then `U` is a type variable.
    """
    type_variables: set[str] = set()

    for node in ast.walk(tree):
        match node:
            case Assign(
                targets=[Name(id=name)],
                value=Call(func=Name(id="TypeVar" | "ParamSpec" | "TypeVarTuple")),
            ):
                type_variables.add(name)

    return type_variables


def get_type_aliases(tree: AST, /) -> set[str]:
    r"""Get all type aliases from AST.

    Examples:
        - `PathLike: TypeAlias = str | Path` (pre 3.12)
        - `type PathLike = str | Path` (post 3.12)
    """
    type_aliases: set[str] = set()

    for node in ast.walk(tree):
        match node:
            case AnnAssign(target=Name(id=name), annotation=Name(id="TypeAlias")):
                type_aliases.add(name)
        if sys.version_info >= (3, 12):
            match node:
                case ast.TypeAlias(name=Name(id=name)):
                    type_aliases.add(name)

    return type_aliases


def get_python_files(
    files_or_pattern: Iterable[str],
    /,
    *,
    root: Optional[Path] = None,
    raise_notfound: bool = True,
    relative_to_root: bool = True,
) -> list[Path]:
    r"""Get all python files from the given list of files or patterns."""
    root = (Path.cwd() if root is None else root).absolute()
    files: list[Path] = []

    for file_or_pattern in files_or_pattern:
        path = Path(file_or_pattern).absolute()
        if path.exists():
            if path.is_file():
                files.append(path)
            if path.is_dir():
                files.extend(path.glob("**/*.py"))
            continue

        # else: path does not exist
        matches = list(root.glob(file_or_pattern))
        if not matches and raise_notfound:
            raise FileNotFoundError(
                f"Pattern {file_or_pattern!r} did not match any files."
            )
        files.extend(matches)

    if relative_to_root:
        files = [file.relative_to(root) for file in files]

    return files


def is_private(s: str, /) -> bool:
    r"""Checks if variable name is considered private.

    References:
        https://stackoverflow.com/a/62865302/9318372
    """
    assert s.isidentifier(), f"{s=} is not an identifier!"
    return s.startswith("_") or (s.startswith("__") and not s.endswith("__"))


def is_dunder(s: str, /) -> bool:
    r"""True if starts and ends with two underscores.

    Roughly equivalent to the regex `^__\w+__$`.
    """
    assert s.isidentifier(), f"{s=} is not an identifier!"
    return (
        s.startswith("__")
        and not s.startswith("___")
        and s.endswith("__")
        and not s.endswith("___")
        and len(s) > 4
    )


def is_package(module: ModuleType, /) -> bool:
    r"""True if module is a package."""
    return module.__name__ in {module.__package__, "__init__"}


def is_module(module: ModuleType, /) -> bool:
    r"""True if module is a non-package module."""
    return module.__name__ not in {module.__package__, "__init__"}


def load_module(file: str | Path, /, *, load_silent: bool = False) -> ModuleType:
    r"""Load a module from a file."""
    path = Path(file)
    assert path.exists(), f"{path=} does not exist!"
    assert path.is_file(), f"{path=} is not a file!"
    assert path.suffix == ".py", f"{path=} is not a python file!"

    # get module specification
    spec = spec_from_file_location(path.stem, path)
    assert spec is not None, f"{path=} has no spec ?!?!"
    assert spec.loader is not None, f"{path=} has no loader ?!?!"

    # load the module silently
    module = module_from_spec(spec)
    with (
        redirect_stdout(None if load_silent else sys.stdout),
        redirect_stderr(None if load_silent else sys.stderr),
    ):
        spec.loader.exec_module(module)

    return module


def check_module(
    pkg: ModuleType,
    /,
    *,
    ignore_dunder_attributes: bool,
    ignore_imports_modules: bool,
    ignore_imports_packages: bool,
    ignore_private_attributes: bool,
    ignore_type_aliases: bool,
    ignore_type_variables: bool,
) -> int:
    r"""Check a single module."""
    violations = 0

    # create logger with custom formatting
    assert pkg.__file__ is not None, f"{pkg=} has no __file__ ?!?!"
    path = Path(pkg.__file__).relative_to(Path.cwd())
    logger = logging.getLogger().getChild(f"{path!s}:0")
    formatter = logging.Formatter(fmt="%(name)s %(message)s", style="%")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False  # don't propagate to root logger

    # get variables
    explicit_names: set[str] = set(getattr(pkg, "__all__", ()))
    exported_names: set[str] = set(vars(pkg))
    excluded_names: set[str] = set()
    max_key_length = max(map(len, exported_names), default=0)

    # remove excluded names
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text)

    if ignore_imports_modules and is_module(pkg):
        excluded_names |= get_imported_names(tree)
    if ignore_imports_packages and is_package(pkg):
        excluded_names |= get_imported_names(tree)
    if ignore_type_variables:
        excluded_names |= get_type_variables(tree)
    if ignore_type_aliases:
        excluded_names |= get_type_aliases(tree)

    # check all names
    for key in exported_names - excluded_names:
        if ignore_dunder_attributes and is_dunder(key):
            logger.debug("%s Skipped! - dunder attribute!", key.ljust(max_key_length))
            continue
        if ignore_private_attributes and is_private(key):
            logger.debug("%s Skipped! - private attribute!", key.ljust(max_key_length))
            continue

        if key not in explicit_names:
            print(f"{path!s}:0 exports {key!r} not listed in __all__!")
            violations += 1

    return violations


def check_file(
    fname: str | Path,
    /,
    *,
    check_modules: bool,
    check_packages: bool,
    check_private: bool,
    ignore_dunder_attributes: bool,
    ignore_imports_modules: bool,
    ignore_imports_packages: bool,
    ignore_private_attributes: bool,
    ignore_type_variables: bool,
    ignore_type_aliases: bool,
    load_silent: bool = True,
    skip_if_all_missing: bool = True,
) -> int:
    r"""Check a single file."""
    path = Path(fname)
    module_name = path.stem
    assert path.exists(), f"{path=} does not exist!"
    assert path.is_file(), f"{path=} is not a file!"
    assert path.suffix == ".py", f"{path=} is not a python file!"

    # determine whether to check the file at all
    if is_private(module_name) and not check_private:
        __logger__.debug('Skipped "%s:0" - private module!', path)
        return 0
    if module_name == "__init__" and not check_packages:
        __logger__.debug('Skipped "%s:0" - Ignoring packages!', path)
        return 0
    if module_name != "__init__" and not check_modules:
        __logger__.debug('Skipped "%s:0" - Ignoring modules!', path)
        return 0

    # load module
    pkg = load_module(path, load_silent=load_silent)
    if set(vars(pkg)) ^ set(dir(pkg)):
        print(f"{path!s}:0 module vars() does not agree with dir() ???")
        return 1

    if skip_if_all_missing and not hasattr(pkg, "__all__"):
        __logger__.debug('Skipped "%s:0" - __all__ missing!', path)
        return 0

    return check_module(
        pkg,
        ignore_imports_modules=ignore_imports_modules,
        ignore_imports_packages=ignore_imports_packages,
        ignore_dunder_attributes=ignore_dunder_attributes,
        ignore_private_attributes=ignore_private_attributes,
        ignore_type_variables=ignore_type_variables,
        ignore_type_aliases=ignore_type_aliases,
    )


def main() -> None:
    r"""Main program."""
    parser = argparse.ArgumentParser(
        description="Use standard generics (PEP-585): typing.Sequence -> abc.Sequence, typing.List -> list.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument(
        "--check-modules",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Whether to check modules, otherwise only checks packages (`__init__.py`-files).",
    )
    parser.add_argument(
        "--check-packages",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Whether to check packages (`__init__.py`-files).",
    )
    parser.add_argument(
        "--check-private",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Whether to check 'private' modules/pacakges, i.e. files starting with a single underscore.",
    )
    parser.add_argument(
        "--ignore-imports-modules",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore imported variables in (non-package) modules.",
    )
    parser.add_argument(
        "--ignore-imports-packages",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Ignore imported variables in packages (__init__.py).",
    )
    parser.add_argument(
        "--ignore-dunder-attributes",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore 'dunder' variables, i.e. attributes starting and ending in double underscores.",
    )
    parser.add_argument(
        "--ignore-private-attributes",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore 'private' variables, i.e. attributes starting with a single underscore.",
    )
    parser.add_argument(
        "--ignore-type-variables",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore type variables.",
    )
    parser.add_argument(
        "--ignore-type-aliases",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore type aliases.",
    )
    parser.add_argument(
        "--skip-if-all-missing",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Skip files that do not contain an __all__ attribute.",
    )
    parser.add_argument(
        "--load-silent",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Load modules silently.",
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
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        __logger__.debug("args: %s", vars(args))

    # find all files
    files: list[Path] = get_python_files(args.files)

    # apply script to all files
    violations = 0
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            violations += check_file(
                file,
                check_modules=args.check_modules,
                check_packages=args.check_packages,
                check_private=args.check_private,
                ignore_imports_modules=args.ignore_imports_modules,
                ignore_imports_packages=args.ignore_imports_packages,
                ignore_dunder_attributes=args.ignore_dunder_attributes,
                ignore_private_attributes=args.ignore_private_attributes,
                ignore_type_aliases=args.ignore_type_aliases,
                ignore_type_variables=args.ignore_type_variables,
                skip_if_all_missing=args.skip_if_all_missing,
                load_silent=args.load_silent,
            )
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
