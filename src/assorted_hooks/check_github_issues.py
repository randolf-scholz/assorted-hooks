"""Checks if referenced issues are closed."""

__all__ = [
    # Constants
    "ISSUE_PATTERN",
    "ISSUE_REGEX",
    # classes
    "IssueMatch",
    # Functions
    "is_closed",
    "check_file",
    "find_issues",
    "find_issues_in_file",
    "main",
]

import argparse
import logging
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from github import Auth, Github

from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)


@dataclass
class IssueMatch:
    r"""Issue reference."""

    line: int
    col: int
    org: str
    repo: str
    number: int

    @property
    def url(self):
        return f"https://github.com/{self.org}/{self.repo}/issues/{self.number}"


ISSUE_PATTERN = (
    r"https:\/\/github\.com\/(?P<org>[\w-]+)\/(?P<repo>[\w-]+)\/issues\/(?P<number>\d+)"
)
r"""Pattern to match issue references."""
ISSUE_REGEX: re.Pattern = re.compile(ISSUE_PATTERN)
r"""Compiled regex for issue references."""


def find_issues(text: str, /) -> Iterator[IssueMatch]:
    r"""Find all issues in the text, as dictionary indexed by line/column number."""
    for line_num, line in enumerate(text.splitlines()):
        for match in ISSUE_REGEX.finditer(line):
            yield IssueMatch(
                line=int(line_num + 1),
                col=match.start() + 1,
                org=match.group("org"),
                repo=match.group("repo"),
                number=int(match.group("number")),
            )


def find_issues_in_file(path: Path, /) -> Iterator[IssueMatch]:
    r"""Find all issues in the file, as dictionary indexed by line/column number."""
    with open(path, encoding="utf8") as file:
        for line_num, line in enumerate(file):
            for match in ISSUE_REGEX.finditer(line):
                yield IssueMatch(
                    line=int(line_num + 1),
                    col=match.start() + 1,
                    org=match.group("org"),
                    repo=match.group("repo"),
                    number=int(match.group("number")),
                )


def is_closed(match: IssueMatch, /, *, git: Github) -> bool:
    r"""Check if the issue is closed."""
    repo = git.get_repo(f"{match.org}/{match.repo}")
    issue = repo.get_issue(number=match.number)
    return issue.state == "closed"


def check_file(filepath: str | Path, /, *, git: Github) -> int:
    r"""Check if issues are closed."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    fname = str(path)
    text = path.read_text(encoding="utf8")

    for issue in find_issues(text):
        if is_closed(issue, git=git):
            violations += 1
            print(f"{fname}:{issue.line}:{issue.col}: Issue {issue.url} is resolved.")

    return violations


def main() -> None:
    r"""Check if issues are closed."""
    parser = argparse.ArgumentParser(
        description="Check if referenced issues are closed.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument(
        "--auth",
        type=str,
        default=None,
        help="GitHub authentication token.",
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

    if args.auth is None:
        raise NotImplementedError(
            "GitHub authentication token is required."
            "Please call with hook manually with additional args `--auth <token>`."
        )

    # authenticate
    git = Github(auth=Auth.Token(args.auth))

    # find all files
    files: list[Path] = get_python_files(args.files)

    # apply script to all files
    violations = 0
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            violations += check_file(file, git=git)
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
