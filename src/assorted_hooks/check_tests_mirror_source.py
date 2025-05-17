#!/usr/bin/env python
r"""Check that tests/ directory structure mirrors /src."""

__all__ = [
    # functions
    "check_tests_mirror_source",
    "main",
]

import argparse
from pathlib import Path


def check_tests_mirror_source(
    src_dir: str | Path,
    tests_dir: str | Path,
    /,
    *,
    disallow_extra_dirs: bool = True,
) -> int:
    r"""Check that tests/ directory structure mirrors /src/."""
    violations = 0
    src_dir = Path(src_dir)
    tests_dir = Path(tests_dir)

    if not (src_dir.exists() and src_dir.is_dir()):
        raise FileNotFoundError(f"Source directory {src_dir} does not exist.")
    if not (tests_dir.exists() and tests_dir.is_dir()):
        raise FileNotFoundError(f"Tests directory {tests_dir} does not exist.")

    # Step 1: Check that for every directory in src_dir, there is a corresponding directory in tests_dir.
    for src_subdir in src_dir.rglob("*"):
        # skip private/hidden directories
        if src_subdir.name.startswith("_") or src_subdir.name.startswith("."):
            continue
        if src_subdir.is_dir():
            relative_path = src_subdir.relative_to(src_dir)
            corresponding_tests_dir = tests_dir / relative_path
            if not corresponding_tests_dir.exists():
                violations += 1
                print(
                    f"\033[34m{corresponding_tests_dir}\033[0m: Missing directory in tests."
                )
    if not disallow_extra_dirs:
        return violations

    # Step 2: Check that there are no extra directories in tests_dir that are not in src_dir.
    #   Note: This only applies to We only consider directories of the form "tests/package_name/**/dir" for which
    #      src/package_name/ exists.
    for tests_subdir in tests_dir.rglob("*"):
        # skip private/hidden directories
        if tests_subdir.name.startswith("_") or tests_subdir.name.startswith("."):
            continue
        if tests_subdir.is_dir():
            # strip the tests_dir prefix from the path
            relative_path = tests_subdir.relative_to(tests_dir)
            # check if it corresponds to the form "tests/package_name/**/dir"
            # and if src_dir/package_name exists
            corresponding_src_dir = src_dir / relative_path
            if Path(*corresponding_src_dir.parts[:2]).exists() and not (
                corresponding_src_dir.exists()
                or corresponding_src_dir.with_suffix(".py").exists()
            ):
                violations += 1
                print(f"\033[34m{tests_subdir}\033[0m: Extra directory not in src.")

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check that tests/ directory structure mirrors /src/",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--src-dir",
        type=str,
        default="src/",
        help="Path to the source directory (e.g., /src/)",
    )
    parser.add_argument(
        "--tests-dir",
        type=str,
        default="tests/",
        help="Path to the tests directory (e.g., /tests/)",
    )
    parser.add_argument(
        "--disallow-extra-dirs",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Check that tests/ does not have directories not in src/",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Enable debug mode.",
    )
    args = parser.parse_args()

    violations = check_tests_mirror_source(
        args.src_dir,
        args.tests_dir,
        disallow_extra_dirs=args.disallow_extra_dirs,
    )

    if violations:
        print(f"Found {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
