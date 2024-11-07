#!/usr/bin/env python
r"""Checks if referenced issues are closed."""

__all__ = [
    # Constants
    "EXCLUDED",
    "REPO_REGEX",
    # Functions
    "check_file",
    "get_fullname",
    "get_repo_urls",
    "main",
    "repo_is_archived",
]

import argparse
import re
from pathlib import Path
from typing import Any, Final

import yaml
from github import Github, RateLimitExceededException

EXCLUDED: Final[frozenset[str]] = frozenset({"local", "META"})
r"""Excluded repositories."""

REPO_REGEX: Final[re.Pattern] = re.compile(
    r"github\.com/(?P<name>(?:[\w-]+/)*[\w-]+)(?:\.git)?"
)
r"""Regular expression to extract the repository name."""


def get_repo_urls(pre_commit_config: dict, /) -> list[str]:
    r"""Get the urls of repositories from the pre-commit configuration."""
    repos: list[dict[str, Any]] = pre_commit_config["repos"]
    urls = [url for spec in repos if (url := spec["repo"]) not in EXCLUDED]
    if not urls:
        raise ValueError("No repositories found in the pre-commit configuration.")
    return urls


def get_fullname(url: str, /) -> str:
    r"""Extract the relevant information from a repository URL."""
    match = REPO_REGEX.search(url)
    if not match:
        raise ValueError(f"Could not extract repository information from {url!r}")
    return match.group("name")


def repo_is_archived(git: Github, url: str, /) -> bool:
    r"""Check if a repository is archived."""
    name = get_fullname(url)
    try:
        repository = git.get_repo(name)
    except RateLimitExceededException:
        print("Rate limit exceeded!")
        raise SystemExit(1) from None
    except Exception as exc:
        raise RuntimeError(f"Could not get repository {name!r}!") from exc

    return repository.archived


def check_file(filepath: str | Path, /) -> int:
    r"""Check the pre-commit configuration file for archived repositories."""
    path = Path(filepath)
    fname = path.name
    with path.open() as file:
        config = yaml.safe_load(file)

    git = Github(timeout=5, retry=False)
    repos = get_repo_urls(config)
    violations = 0

    for repo in repos:
        if repo_is_archived(git, repo):
            violations += 1
            print(f"{fname!s} Repository {repo} is archived.")

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Checks for unmaintained dependencies.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "pre_commit_file",
        nargs="?",
        default=".pre-commit-config.yaml",
        type=str,
        help="The path to the pre-commit config file.",
    )
    args = parser.parse_args()

    try:
        violations = check_file(args.pre_commit_file)
    except Exception as exc:
        exc.add_note(f'Checking file "{args.pre_commit_file!s}" failed!')
        raise

    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
