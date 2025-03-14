r"""Assorted Hooks."""

__all__ = [
    # constants
    "__version__",
    # module
    "check_archived_hooks",
    "check_github_issues",
    "check_requirements_maintained",
    "check_requirements_valid",
]


from importlib import metadata

from assorted_hooks import (
    check_archived_hooks,
    check_github_issues,
    check_requirements_maintained,
    check_requirements_valid,
)

try:  # single-source version
    __version__ = metadata.version(__package__ or __name__)
except metadata.PackageNotFoundError:
    __version__ = "0"

del metadata
