"""Some utility functions for assorted_hooks."""

__all__ = [
    # Constants
    "KEYWORDS",
    "SOFT_KEYWORDS",
    "BUILTIN_FUNCTIONS",
    "BUILTIN_CONSTANTS",
    "BUILTIN_SITE_CONSTANTS",
    "BUILTIN_EXCEPTIONS",
    # Functions
    "get_python_files",
]

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


KEYWORDS: list[str] = [
    # fmt: off
    "False"     , "await",      "else",       "import",     "pass",
    "None"      , "break",      "except",     "in",         "raise",
    "True"      , "class",      "finally",    "is",         "return",
    "and"       , "continue",   "for",        "lambda",     "try",
    "as"        , "def",        "from",       "nonlocal",   "while",
    "assert"    , "del",        "global",     "not",        "with",
    "async"     , "elif",       "if",         "or",         "yield",
    # fmt: on
]
"""Python builtin keywords, cf. https://docs.python.org/3/reference/lexical_analysis.html#keywords."""


SOFT_KEYWORDS: list[str] = ["match", "case", "_"]
"""Python soft keywords, cf. https://docs.python.org/3/reference/lexical_analysis.html#soft-keywords."""

BUILTIN_FUNCTIONS: list[str] = [
    # fmt: off
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
]
"""Builtin functions, cf. https://docs.python.org/3/library/functions.html."""

BUILTIN_CONSTANTS: list[str] = [
    "False",
    "None",
    "True",
    "NotImplemented",
    "Ellipsis",
    "__debug__",
]
"""Builtin constants, cf. https://docs.python.org/3/library/constants.html."""

BUILTIN_SITE_CONSTANTS: list[str] = ["copyright", "credits", "license", "exit", "quit"]
"""cf. https://docs.python.org/3/library/constants.html#constants-added-by-the-site-module"""

BUILTIN_EXCEPTIONS: list[str] = [
    # fmt: off
    # A
    "ArithmeticError", "AssertionError", "AttributeError",
    # B
    "BaseException", "BlockingIOError", "BrokenPipeError", "BufferError", "BytesWarning",
    # C
    "ChildProcessError", "ConnectionAbortedError", "ConnectionError", "ConnectionRefusedError", "ConnectionResetError",
    # D
    "DeprecationWarning",
    # E
    "EOFError", "EncodingWarning", "EnvironmentError", "Exception",
    # F
    "FileExistsError", "FileNotFoundError", "FloatingPointError", "FutureWarning",
    # G
    "GeneratorExit",
    # I
    "IOError", "ImportError", "ImportWarning", "IndentationError", "IndexError", "InterruptedError", "IsADirectoryError",
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
    "StopAsyncIteration", "StopIteration", "SyntaxError", "SyntaxWarning", "SystemError", "SystemExit",
    # T
    "TabError", "TimeoutError", "TypeError",
    # U
    "UnboundLocalError", "UnicodeDecodeError", "UnicodeEncodeError", "UnicodeError", "UnicodeTranslateError", "UnicodeWarning", "UserWarning",
    # V
    "ValueError",
    # W
    "Warning",
    # Z
    "ZeroDivisionError",
    # fmt: on
]
"""Builtin exceptions, cf. https://docs.python.org/3/library/exceptions.html."""
