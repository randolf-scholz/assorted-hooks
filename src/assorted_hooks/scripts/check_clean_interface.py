#!/usr/bin/env python
"""Check for clean interface."""

__all__ = [
    "check_file",
    "check_module",
    "get_python_files",
    "is_dunder",
    "is_package",
    "is_private",
    "main",
]

import argparse
import logging
import sys
from collections.abc import Iterable
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Optional

__logger__ = logging.getLogger(__name__)


def get_python_files(
    files_or_pattern: Iterable[str],
    /,
    *,
    root: Optional[Path] = None,
    raise_notfound: bool = True,
    relative_to_root: bool = True,
) -> list[Path]:
    """Get all python files from the given list of files or patterns."""
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
    """True if starts exactly a single underscore."""
    assert s.isidentifier(), f"{s=} is not an identifier!"
    return s.startswith("_") and not s.startswith("__")


def is_dunder(s: str, /) -> bool:
    """True if starts and ends with two underscores."""
    assert s.isidentifier(), f"{s=} is not an identifier!"
    return (
        s.startswith("__")
        and not s.startswith("___")
        and s.endswith("__")
        and not s.endswith("___")
    )


def is_package(module: ModuleType, /) -> bool:
    """True if module is a package."""
    return (module.__name__ == module.__package__) or module.__name__ == "__init__"


def check_module(
    module: ModuleType,
    /,
    *,
    ignore_dunder_attributes: bool,
    ignore_non_packages: bool,
    ignore_private_attributes: bool,
    ignore_private_modules: bool,
) -> bool:
    """Check a single module."""
    passed = True

    module_name = module.__name__
    assert module.__file__ is not None, f"{module_name=} has no __file__ ?!?!"
    path = Path(module.__file__).relative_to(Path.cwd())

    # create logger with custom formatting
    logger = logging.getLogger().getChild(f"{path!s}:0")
    formatter = logging.Formatter(fmt="%(name)s %(message)s", style="%")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False  # don't propagate to root logger

    if ignore_non_packages and not is_package(module):
        logger.debug("Skipped! - not a package!")
        return True
    if ignore_private_modules and is_private(module_name):
        logger.debug("Skipped! - private module!")
        return True
    if set(vars(module)) ^ set(dir(module)):
        print(f"{path!s}:0 module vars() does not agree with dir() ???")
        return False
    if hasattr(module, "__all__"):
        exported_keys = module.__all__
    else:
        exported_keys = []

    # get max length of variable names
    max_length = max(map(len, dir(module)), default=0)

    # check all keys
    for key in vars(module):
        if ignore_dunder_attributes and is_dunder(key):
            # logger.debug(f"%s Skipped! - dunder attribute!", key.ljust(max_length))
            continue
        if ignore_private_attributes and is_private(key):
            logger.debug("%s Skipped! - private attribute!", key.ljust(max_length))
            continue

        if key not in exported_keys:
            passed = False
            print(f"{path!s}:0 {module_name!r} exports {key!r} not listed in __all__!")

    return passed


def check_file(
    fname: str | Path,
    /,
    *,
    ignore_dunder_attributes: bool,
    ignore_non_packages: bool,
    ignore_private_attributes: bool,
    ignore_private_modules: bool,
) -> bool:
    """Check a single file."""
    path = Path(fname)
    module_name = path.stem

    # check if private
    if ignore_private_modules and is_private(module_name):
        __logger__.debug('Skipped "%s:0" - private module!', path)
        return True

    # load module
    spec = spec_from_file_location(module_name, path)
    assert spec is not None, f"{path=} has no spec ?!?!"
    assert spec.loader is not None, f"{path=} has no loader ?!?!"
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    return check_module(
        module,
        ignore_dunder_attributes=ignore_dunder_attributes,
        ignore_non_packages=ignore_non_packages,
        ignore_private_attributes=ignore_private_attributes,
        ignore_private_modules=ignore_private_modules,
    )


def main() -> None:
    """Main program."""
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
        "--ignore-dunder-attributes",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore 'dunder' attributes, i.e. attributes starting and ending in double underscores.",
    )
    parser.add_argument(
        "--ignore-private-attributes",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore 'private' attributes, i.e. attributes starting with a single underscore.",
    )
    parser.add_argument(
        "--ignore-non-packages",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore modules, i.e. only check packages (__init__.py files).",
    )
    parser.add_argument(
        "--ignore-private-modules",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore 'private' modules, i.e. files starting with a single underscore.",
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
    passed = True
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            passed &= check_file(
                file,
                ignore_dunder_attributes=args.ignore_dunder_attributes,
                ignore_non_packages=args.ignore_non_packages,
                ignore_private_attributes=args.ignore_private_attributes,
                ignore_private_modules=args.ignore_private_modules,
            )
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
