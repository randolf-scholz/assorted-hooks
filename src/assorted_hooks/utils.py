"""Some utility functions for assorted_hooks."""

__all__ = [
    # Constants
    "KEYWORDS",
    "SOFT_KEYWORDS",
    "BUILTIN_FUNCTIONS",
    "BUILTIN_CONSTANTS",
    "BUILTIN_SITE_CONSTANTS",
    "BUILTIN_EXCEPTIONS",
    # Protocols
    "FileCheck",
    # Functions
    "check_all_files",
    "get_python_files",
]

import argparse
from collections.abc import Iterable
from pathlib import Path
from typing import Optional, Protocol


class FileCheck(Protocol):
    r"""Protocol for file checks."""

    def __call__(self, file: Path, /, *, options: argparse.Namespace) -> int: ...


def get_python_files(
    files_or_pattern: Iterable[str],
    /,
    *,
    root: Optional[Path] = None,
    raise_notfound: bool = True,
    relative_to_root: bool = False,
) -> list[Path]:
    r"""Get all python files from the given list of files or patterns."""
    paths: list[Path] = [Path(item).absolute() for item in files_or_pattern]

    # determine the root directory
    if root is None:
        root = (
            paths[0] if len(paths) == 1 and paths[0].is_dir() else Path.cwd().absolute()
        )

    files: list[Path] = []
    for path in paths:
        if path.exists():
            if path.is_file():
                files.append(path)
            if path.is_dir():
                files.extend(path.glob("**/*.py"))
            continue

        # else: path does not exist
        matches = list(root.glob(path.name))
        if not matches and raise_notfound:
            raise FileNotFoundError(f"Pattern {path!r} did not match any files.")
        files.extend(matches)

    if relative_to_root:
        files = [file.relative_to(root) for file in files]

    return files


def check_all_files(*checks: FileCheck, options: argparse.Namespace) -> None:
    # find all files
    files: list[Path] = get_python_files(options.files)

    violations = 0

    # apply script to all files
    for file in files:
        print(f"Checking {file!s}")
        for check in checks:
            try:
                violations += check(file, options=options)
            except Exception as exc:
                raise RuntimeError(
                    f"{file!s}: Performing check {check!r} failed!"
                ) from exc

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")
        raise SystemExit(1)


KEYWORDS: list[str] = [
    "False"     , "await",      "else",       "import",     "pass",
    "None"      , "break",      "except",     "in",         "raise",
    "True"      , "class",      "finally",    "is",         "return",
    "and"       , "continue",   "for",        "lambda",     "try",
    "as"        , "def",        "from",       "nonlocal",   "while",
    "assert"    , "del",        "global",     "not",        "with",
    "async"     , "elif",       "if",         "or",         "yield",
]  # fmt: skip
r"""Python builtin keywords, cf. https://docs.python.org/3/reference/lexical_analysis.html#keywords."""


SOFT_KEYWORDS: list[str] = ["match", "case", "_"]
r"""Python soft keywords, cf. https://docs.python.org/3/reference/lexical_analysis.html#soft-keywords."""

BUILTIN_FUNCTIONS: list[str] = [
    # A
    "abs", "aiter", "all", "anext", "any", "ascii",
    # B
    "bin", "bool", "breakpoint", "bytearray", "bytes",
    # C
    "callable", "chr", "classmethod", "compile", "complex",
    # D
    "delattr", "dict", "dir", "divmod",
    # E
    "enumerate", "eval", "exec",
    # F
    "filter", "float", "format", "frozenset",
    # G
    "getattr", "globals",
    # H
    "hasattr", "hash", "help", "hex",
    # I
    "id", "input", "int", "isinstance", "issubclass", "iter",
    # L
    "len", "list", "locals",
    # M
    "map", "max", "memoryview", "min",
    # N
    "next",
    # O
    "object", "oct", "open", "ord",
    # P
    "pow", "print", "property",
    # R
    "range", "repr", "reversed", "round",
    # S
    "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super",
    # T
    "tuple", "type",
    # V
    "vars",
    # Z
    "zip",
    # _
    "__import__",
]  # fmt: skip
r"""Builtin functions, cf. https://docs.python.org/3/library/functions.html."""

BUILTIN_CONSTANTS: list[str] = [
    "False",
    "None",
    "True",
    "NotImplemented",
    "Ellipsis",
    "__debug__",
]
r"""Builtin constants, cf. https://docs.python.org/3/library/constants.html."""

BUILTIN_SITE_CONSTANTS: list[str] = ["copyright", "credits", "license", "exit", "quit"]
r"""cf. https://docs.python.org/3/library/constants.html#constants-added-by-the-site-module"""

BUILTIN_EXCEPTIONS: list[str] = [
    # A
    "ArithmeticError", "AssertionError", "AttributeError",
    # B
    "BaseException", "BlockingIOError", "BrokenPipeError", "BufferError",
    "BytesWarning",
    # C
    "ChildProcessError", "ConnectionAbortedError", "ConnectionError",
    "ConnectionRefusedError", "ConnectionResetError",
    # D
    "DeprecationWarning",
    # E
    "EOFError", "EncodingWarning", "EnvironmentError", "Exception",
    # F
    "FileExistsError", "FileNotFoundError", "FloatingPointError", "FutureWarning",
    # G
    "GeneratorExit",
    # I
    "IOError", "ImportError", "ImportWarning", "IndentationError", "IndexError",
    "InterruptedError", "IsADirectoryError",
    # K
    "KeyError", "KeyboardInterrupt",
    # L
    "LookupError",
    # M
    "MemoryError", "ModuleNotFoundError",
    # N
    "NameError", "NotADirectoryError", "NotImplemented", "NotImplementedError",
    # O
    "OSError", "OverflowError",
    # P
    "PendingDeprecationWarning", "PermissionError", "ProcessLookupError",
    # R
    "RecursionError", "ReferenceError", "ResourceWarning", "RuntimeError", "RuntimeWarning",
    # S
    "StopAsyncIteration", "StopIteration", "SyntaxError", "SyntaxWarning",
    "SystemError", "SystemExit",
    # T
    "TabError", "TimeoutError", "TypeError",
    # U
    "UnboundLocalError", "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeError",
    "UnicodeTranslateError", "UnicodeWarning", "UserWarning",
    # V
    "ValueError",
    # W
    "Warning",
    # Z
    "ZeroDivisionError",
]  # fmt: skip
r"""Builtin exceptions, cf. https://docs.python.org/3/library/exceptions.html."""
