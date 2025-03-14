#!/usr/bin/env python
r"""Check consistent spelling of "-wise" suffix.

Finds all occurances of words like "elementwise" or "element-wise" and checks
if the spelling is consistent throughout the repository.
"""

__all__ = [
    "Match",
    "PATTERN",
    "check_files",
    "get_matches",
    "main",
]

import argparse
import re
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import Final, NamedTuple

PATTERN: Final[re.Pattern] = re.compile(r"\b(?P<name>\w+)[\s-]?wise\b")


class Match(NamedTuple):
    r"""Match object."""

    file: str
    row: int
    col: int
    name: str
    match: str


def get_matches(path: Path) -> Iterator[Match]:
    r"""Get all matches in a file."""
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            for match in PATTERN.finditer(line):
                yield Match(
                    file=path.name,
                    row=line_number,
                    col=match.start() + 1,
                    name=match.group("name"),
                    match=match.group(0),
                )


def check_files(*files: str) -> int:
    r"""Main program."""
    cases: dict[str, list[Match]] = defaultdict(list)

    for file in files:
        path = Path(file)
        if not path.is_file():
            raise FileNotFoundError(f"{path} is not a file.")

        for match in get_matches(path):
            cases[match.name].append(match)

    violations = 0
    for samples in cases.values():
        # check if the spelling is unique
        if len({sample.match for sample in samples}) == 1:
            continue
        # otherwise, print all occurances
        for sample in samples:
            violations += 1
            fname = sample.file
            row = sample.row
            col = sample.col
            print(f"{fname}:{row}:{col}: Inconsistent spelling: {sample.match!r}")
    return violations


def main() -> None:
    r"""Main program."""
    parser = argparse.ArgumentParser(
        description="Check consistent spelling of '-wise' suffix.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("files", nargs="+", type=str, help="Files to check.")
    args = parser.parse_args()

    try:
        violations = check_files(*args.files)
    except Exception as exc:
        raise RuntimeError("Checking files failed!") from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
