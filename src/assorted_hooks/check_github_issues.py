#!/usr/bin/env python
r"""Checks if referenced issues are closed."""

__all__ = [
    # Constants
    "ISSUE_REGEX",
    # classes
    "IssueMatch",
    # Functions
    "authenticate",
    "authenticate_token",
    "authenticate_query",
    "check_file",
    "find_issues",
    "find_issues_in_file",
    "is_closed_issue",
    "main",
]

import argparse
import getpass
import logging
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from github import Auth, Github
from github.GithubException import BadCredentialsException, RateLimitExceededException

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
    comment: int | None = None

    @property
    def url(self) -> str:
        url = f"https://github.com/{self.org}/{self.repo}/issues/{self.number}"
        if self.comment is not None:
            url += f"#issuecomment-{self.comment}"
        return url


ISSUE_REGEX: re.Pattern = re.compile(r"""(?x:  # verbose regex
    https://github\.com/
    (?P<org>[\w-]+)/
    (?P<repo>[\w-]+)/
    issues/(?P<number>\d+)
    (?:\#issuecomment-(?P<comment>\d+))?
)""")
r"""Compiled regex for issue references."""


def find_issues(text: str, /, *, pattern: re.Pattern) -> Iterator[IssueMatch]:
    r"""Find all issues in the text, as dictionary indexed by line/column number."""
    for line_num, line in enumerate(text.splitlines()):
        for match in pattern.finditer(line):
            yield IssueMatch(
                line=int(line_num + 1),
                col=match.start() + 1,
                org=match.group("org"),
                repo=match.group("repo"),
                number=int(match.group("number")),
                comment=int(match.group("comment")) if match.group("comment") else None,
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
                    comment=int(match.group("comment"))
                    if match.group("comment")
                    else None,
                )


def is_closed_issue(match: IssueMatch, /, *, git: Github) -> bool:
    r"""Check if the issue is closed."""
    try:
        repo = git.get_repo(f"{match.org}/{match.repo}")
        issue = repo.get_issue(number=match.number)
    except RateLimitExceededException:
        # TODO: Ask user for credentials and retry
        print("Rate limit exceeded!")
        raise SystemExit(1) from None
    return issue.state == "closed"


def authenticate_query() -> Github:
    r"""Ask the user for authentication."""
    for k in range(3):
        msg = (
            "\nInvalid credentials! Please try again." * (k > 0)
            + "\nGitHub authentication token is required:"
        )
        auth = getpass.getpass(msg)

        git = Github(auth=Auth.Token(auth))

        try:
            _ = git.get_user().login
        except BadCredentialsException:
            continue
        else:
            return git

    raise RuntimeError("Failed to authenticate with GitHub (max retries reached).")


def authenticate_token(auth: str, /) -> Github:
    r"""Authenticate with GitHub."""
    git = Github(auth=Auth.Token(auth))

    try:
        _ = git.get_user().login
    except BadCredentialsException:
        raise RuntimeError("Invalid GitHub authentication token.") from None

    return git


def authenticate(auth: str | None, /) -> Github:
    r"""Authenticate with GitHub."""
    if auth is None:
        return authenticate_query()
    return authenticate_token(auth)


def check_file(
    filepath: str | Path,
    /,
    *,
    git: Github,
    prefix: str = r"FIXME:\s*",
    ignore_comments: bool = True,
) -> int:
    r"""Check if issues are closed."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    fname = str(path)
    text = path.read_text(encoding="utf8")
    pattern = re.compile(rf"{prefix}{ISSUE_REGEX.pattern}")

    for issue in find_issues(text, pattern=pattern):
        if ignore_comments and issue.comment is not None:
            continue
        if is_closed_issue(issue, git=git):
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
        "--ignore-comments",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Ignore urls that point to comments on issues rather than issues themselves.",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=r"FIXME:\s*",
        help="Regular expression for the prefix of the issue.",
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

    # authenticate
    git = Github(timeout=5, retry=False)  # authenticate(args.auth)

    # find all files
    files: list[Path] = get_python_files(args.files)

    # apply script to all files
    violations = 0
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            violations += check_file(
                file,
                git=git,
                ignore_comments=args.ignore_comments,
                prefix=args.prefix,
            )
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Checking file failed!") from exc

    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
