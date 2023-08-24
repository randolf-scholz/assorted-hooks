"""Some utility functions for assorted_hooks."""

__all__ = ["get_python_files"]

from collections.abc import Iterable
from pathlib import Path
from typing import Optional


def get_python_files(
    files_or_pattern: Iterable[str],
    /,
    *,
    root: Optional[Path] = None,
    raise_notfound: bool = True,
) -> list[Path]:
    """Get all python files from the given list of files or patterns."""
    root = Path.cwd().absolute() if root is None else root.absolute()
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

    return files
