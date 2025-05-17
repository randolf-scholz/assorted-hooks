r"""Constants for assorted_hooks."""

__all__ = [
    "BUILTIN_CONSTANTS",
    "BUILTIN_EXCEPTIONS",
    "BUILTIN_FUNCTIONS",
    "BUILTIN_SITE_CONSTANTS",
    "KEYWORDS",
    "SOFT_KEYWORDS",
    "DUNDER_METHODS_WITH_ARGS",
]


KEYWORDS: list[str] = [
    "False"     , "await",      "else",       "import",     "pass",
    "None"      , "break",      "except",     "in",         "raise",
    "True"      , "class",      "finally",    "is",         "return",
    "and"       , "continue",   "for",        "lambda",     "try",
    "as"        , "def",        "from",       "nonlocal",   "while",
    "assert"    , "del",        "global",     "not",        "with",
    "async"     , "elif",       "if",         "or",         "yield",
]  # fmt: skip
r"""Python builtin keywords, see: https://docs.python.org/3/reference/lexical_analysis.html#keywords."""

SOFT_KEYWORDS: list[str] = ["match", "case", "_"]
r"""Python soft keywords, see: https://docs.python.org/3/reference/lexical_analysis.html#soft-keywords."""

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
r"""Builtin functions, see: https://docs.python.org/3/library/functions.html."""

BUILTIN_CONSTANTS: list[str] = [
    "False",
    "None",
    "True",
    "NotImplemented",
    "Ellipsis",
    "__debug__",
]
r"""Builtin constants, see: https://docs.python.org/3/library/constants.html."""

BUILTIN_SITE_CONSTANTS: list[str] = ["copyright", "credits", "license", "exit", "quit"]
r"""Extra constants, see: https://docs.python.org/3/library/constants.html#constants-added-by-the-site-module"""

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
r"""Builtin exceptions, see: https://docs.python.org/3/library/exceptions.html."""

DUNDER_METHODS_WITH_ARGS: frozenset[str] = frozenset({
    "__add__",
    "__and__",
    "__contains__",
    "__deepcopy__",
    "__delattr__",
    "__delete__",
    "__delitem__",
    "__divmod__",
    "__eq__",
    "__exit__",
    "__floordiv__",
    "__format__",
    "__ge__",
    "__get__",
    "__getattr__",
    "__getattribute__",
    "__getitem__",
    "__gt__",
    "__iadd__",
    "__iand__",
    "__ifloordiv__",
    "__ilshift__",
    "__imatmul__",
    "__imod__",
    "__imul__",
    "__instancecheck__",
    "__ior__",
    "__ipow__",
    "__irshift__",
    "__isub__",
    "__itruediv__",
    "__ixor__",
    "__le__",
    "__lshift__",
    "__lt__",
    "__matmul__",
    "__mod__",
    "__mro_entries__",
    "__mul__",
    "__ne__",
    "__or__",
    "__pow__",
    "__radd__",
    "__rand__",
    "__rdivmod__",
    "__reduce_ex__",
    "__rfloordiv__",
    "__rlshift__",
    "__rmatmul__",
    "__rmod__",
    "__rmul__",
    "__ror__",
    "__round__",
    "__rpow__",
    "__rrshift__",
    "__rshift__",
    "__rsub__",
    "__rtruediv__",
    "__rxor__",
    "__set__",
    "__set_name__",
    "__setattr__",
    "__setitem__",
    "__setstate__",
    "__sub__",
    "__subclasscheck__",
    "__truediv__",
    "__xor__",
})
r"""Dunder methods that take arguments."""
