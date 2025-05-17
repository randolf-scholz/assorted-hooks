r"""Constants for assorted_hooks."""
# ruff: noqa: B033

__all__ = [
    "BUILTIN_CONSTANTS",
    "BUILTIN_EXCEPTIONS",
    "BUILTIN_FUNCTIONS",
    "BUILTIN_SITE_CONSTANTS",
    "KEYWORDS",
    "SOFT_KEYWORDS",
    "OPERATORS",
    "KNOWN_DUNDER_METHODS",
    "KNOWN_DUNDER_ATTRIBUTES",
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

OPERATORS: frozenset[str] = frozenset({
    # unary
    "__abs__", # abs()
    "__pos__", # +
    "__neg__", # -
    "__invert__", # ~
    "__index__", # __index__()
    # arithmetic
    "__add__", "__radd__", "__iadd__",  # +
    "__sub__", "__rsub__", "__isub__",  # -
    "__mul__", "__rmul__", "__imul__",  # *
    "__mod__", "__rmod__", "__imod__",  # %
    "__pow__", "__rpow__", "__ipow__",  # **
    "__matmul__", "__rmatmul__", "__imatmul__",        # @
    "__truediv__", "__rtruediv__", "__itruediv__",     # /
    "__floordiv__", "__rfloordiv__", "__ifloordiv__",  # //
    # bitwise
    "__or__", "__ror__", "__ior__",     # |
    "__and__", "__rand__", "__iand__",  # &
    "__xor__", "__rxor__", "__ixor__",  # ^
    "__lshift__", "__rlshift__", "__ilshift__",  # <<
    "__rshift__", "__rrshift__", "__irshift__",  # >>
    # comparison
    "__eq__",  # ==
    "__ne__",  # !=
    "__lt__",  # <
    "__le__",  # <=
    "__gt__",  # >
    "__ge__",  # >=
    # indexing
    "__getitem__", "__setitem__", "__delitem__",  # []
})  # fmt: skip
r"""Operators that are dunder methods, see: https://docs.python.org/3/library/operator.html."""


KNOWN_DUNDER_METHODS: frozenset[str] = frozenset({
    # 3.2.10.2. Special methods
    # SEE: https://docs.python.org/3/reference/datamodel.html#special-methods
    "__subclasses__",  # (cls) -> list[type]
    # 3.3.1. Basic customization
    # SEE: https://docs.python.org/3/reference/datamodel.html#basic-customization
    "__new__",     # (cls, *args: Any, **kwargs: Any) -> object
    "__init__",    # (self, *args: Any, **kwargs: Any) -> None
    "__del__",     # (self) -> None
    "__repr__",    # (self) -> str
    "__str__",     # (self) -> str
    "__bytes__",   # (self) -> bytes
    "__format__",  # (self, format_spec: str) -> str
    "__lt__",      # (self, other: Any) -> bool
    "__le__",      # (self, other: Any) -> bool
    "__eq__",      # (self, other: Any) -> bool
    "__ne__",      # (self, other: Any) -> bool
    "__gt__",      # (self, other: Any) -> bool
    "__ge__",      # (self, other: Any) -> bool
    "__hash__",    # (self) -> int
    "__bool__",    # (self) -> bool
    # 3.3.2. Customizing attribute access
    # SEE: https://docs.python.org/3/reference/datamodel.html#customizing-attribute-access
    "__dir__",           # (self) -> list[str]
    "__getattribute__",  # (self, name: str) -> Any
    "__getattr__",       # (self, name: str) -> Any
    "__setattr__",       # (self, name: str, value: Any) -> None
    "__delattr__",       # (self, name: str) -> None
    # descriptor methods
    "__get__",       # (self, instance: Any, owner: type) -> Any
    "__set__",       # (self, instance: Any, value: Any) -> None
    "__delete__",    # (self, instance: Any) -> None
    "__objclass__",  # (self) -> type
    # 3.3.3. Customizing class creation
    # SEE: https://docs.python.org/3/reference/datamodel.html#customizing-class-creation
    "__init_subclass__",  # (cls, subclass: type) -> None
    "__set_name__",       # (self, owner: type, name: str) -> None
    "__mro_entries__",    # (cls, bases: tuple[type, ...]) -> tuple[type, ...]
    "__prepare__",        # (metacls, name: str, bases: tuple[type, ...], /, **kwds: Any) -> MutableMapping[str, object]
    # 3.3.4. Customizing instance and subclass checks
    # SEE: https://docs.python.org/3/reference/datamodel.html#customizing-instance-and-subclass-checks
    "__instancecheck__",  # (cls, instance: Any) -> bool
    "__subclasscheck__",  # (cls, subclass: type) -> bool
    # 3.3.5. Emulating generic types
    # SEE: https://docs.python.org/3/reference/datamodel.html#emulating-generic-types
    "__class_getitem__", # (cls, item: Any) -> type
    # 3.3.6. Emulating callable objects
    # SEE: https://docs.python.org/3/reference/datamodel.html#emulating-callable-objects
    "__call__",        # (self, *args: Any, **kwargs: Any) -> Any
    # 3.3.7. Emulating container types
    # SEE: https://docs.python.org/3/reference/datamodel.html#emulating-container-types
    "__len__",      # (self) -> int
    "__iter__",     # (self) -> Iterator[Any]
    "__contains__", # (self, item: Any) -> bool
    "__reversed__", # (self) -> Iterator[Any]
    "__getitem__",  # (self, index: int | slice) -> Any
    "__setitem__",  # (self, index: int | slice, value: Any) -> None
    "__delitem__",  # (self, index: int | slice) -> None
    "__missing__",  # (self, key: Any) -> Any
    # 3.3.8. Emulating numeric types
    # SEE: https://docs.python.org/3/reference/datamodel.html#emulating-numeric-types
    # conversion
    "__bool__",    # (self) -> bool
    "__complex__", # (self) -> complex
    "__float__",   # (self) -> float
    "__int__",     # (self) -> int
    # integer methods
    "__index__",  # (self) -> int
    "__divmod__",  # (self, other: int) -> tuple[int, int]
    # float methods
    "__floor__",  # (self) -> int
    "__ceil__",   # (self) -> int
    "__trunc__",  # (self) -> int
    "__round__",  # (self, ndigits: int | None) -> int | float
    # unary
    "__abs__", # abs()
    "__pos__", # +
    "__neg__", # -
    "__invert__", # ~
    "__index__", # __index__()
    # arithmetic
    "__add__", "__radd__", "__iadd__",  # +
    "__sub__", "__rsub__", "__isub__",  # -
    "__mul__", "__rmul__", "__imul__",  # *
    "__mod__", "__rmod__", "__imod__",  # %
    "__pow__", "__rpow__", "__ipow__",  # **
    "__matmul__", "__rmatmul__", "__imatmul__",        # @
    "__truediv__", "__rtruediv__", "__itruediv__",     # /
    "__floordiv__", "__rfloordiv__", "__ifloordiv__",  # //
    # bitwise
    "__or__", "__ror__", "__ior__",     # |
    "__and__", "__rand__", "__iand__",  # &
    "__xor__", "__rxor__", "__ixor__",  # ^
    "__lshift__", "__rlshift__", "__ilshift__",  # <<
    "__rshift__", "__rrshift__", "__irshift__",  # >>
    # 3.3.9. With Statement Context Managers
    # SEE: https://docs.python.org/3/reference/datamodel.html#with-statement-context-managers
    "__enter__",  # (self) -> ...
    "__exit__",  # (self, exc_type, exc_value, traceback) -> ...
    # 3.3.11. Emulating buffer types
    # SEE: https://docs.python.org/3/reference/datamodel.html#emulating-buffer-types
    "__buffer__",  # (self, flags: int) -> memoryview
    "__release_buffer__",  # (self, buffer: memoryview) -> None
    # 3.4. Coroutines
    # SEE: https://docs.python.org/3/reference/datamodel.html#coroutines
    "__await__",   # (self) -> Iterator[Any]
    "__aiter__",   # (self) -> AsyncIterator[Any]
    "__anext__",   # (self) -> Awaitable[Any]
    "__aenter__",  # (self) -> Awaitable[Any]
    "__aexit__",   # (self, exc_type, exc_value, traceback) -> Awaitable[Any]
    # dataclasses
    # SEE: https://docs.python.org/3/library/dataclasses.html#dataclasses
    "__post_init__",  # (self) -> None
    # abc
    # SEE: https://docs.python.org/3/library/abc.html
    "__subclasshook__",  # (cls, subclass: type) -> bool
    # os
    # SEE: https://docs.python.org/3/library/os.html
    "__fspath__"  # (self) -> str | bytes
    # copy
    # SEE: https://docs.python.org/3/library/copy.html
    "__copy__",  # (self) -> Any
    "__deepcopy__",  # (self, memo: dict[int, Any]) -> Any
    "__replace__",  # (self, /, **kwargs: Any) -> Any
    # pickle
    # SEE: https://docs.python.org/3/library/pickle.html
    "__reduce__",  # (self) -> tuple[type, tuple[Any, ...], dict[str, Any], str | None, str | None]
    "__reduce_ex__",  # (self, protocol: int) -> tuple[type, tuple[Any, ...], dict[str, Any], str | None, str | None]
    "__setstate__",  # (self, state: Any) -> None
    "__getstate__",  # (self) -> Any
    "__getnewargs__",  # (self) -> tuple[Any, ...]
    "__getnewargs_ex__",  # (self) -> tuple[tuple[Any, ...], dict[str, Any]]
    # sys
    # SEE: https://docs.python.org/3/library/sys.html
    "__sizeof__",  # (self) -> int
})  # fmt: skip


KNOWN_DUNDER_ATTRIBUTES: frozenset[str] = frozenset({
    # constants (https://docs.python.org/3/library/constants.html)
    "__debug__",  # bool
    # modules
    "__all__",  # list[str]
    "__version__"  # str
    # 3.2.8. Callable types
    # SEE: https://docs.python.org/3/reference/datamodel.html#callable-types
    "__globals__",  # dict[str, Any]
    "__closure__",  # tuple[Cell, ...]
    "__doc__",  # str | None
    "__name__",  # str
    "__qualname__",  # str
    "__module__",  # str
    "__defaults__",  # tuple[Any, ...] | None
    "__code__",  # CodeType
    "__dict__",  # dict[str, Any]
    "__annotations__",  # dict[str, type]
    "__kwdefaults__",  # dict[str, Any] | None
    "__type_params__",  # tuple[type, ...]
    # methods
    "__self__",  # object
    "__func__",  # function
    "__doc__",  # str | None
    "__name__",  # str
    "__module__",  # str
    # 3.2.9. Modules
    # SEE: https://docs.python.org/3/reference/datamodel.html#modules
    "__name__",  # str
    "__spec__",  # str
    "__package__",  # str
    "__loader__",  # str
    "__path__",  # str
    "__file__",  # str
    "__cached__",  # str
    "__doc__",  # str
    "__annotations__",  # dict[str, type]
    "__dict__",  # dict[str, Any]
    # 3.2.10. Custom classes
    # SEE: https://docs.python.org/3/reference/datamodel.html#custom-classes
    "__name__",  # str
    "__qualname__",  # str
    "__module__",  # str
    "__dict__",  # dict[str, Any]
    "__bases__",  # tuple[type, ...]
    "__doc__",  # str | None
    "__annotations__",  # dict[str, type]
    "__type_params__",  # tuple[type, ...]
    "__static_attributes__",  # dict[str, type]
    "__firstlineno__",  # int
    "__mro__",  # tuple[type, ...]
    # 3.2.11. Class instances
    # SEE: https://docs.python.org/3/reference/datamodel.html#class-instances
    "__class__",  # type
    "__dict__",  # dict[str, Any]
    # 3.3.2.4. __slots__
    # SEE: https://docs.python.org/3/reference/datamodel.html#slots
    "__slots__",  # tuple[str, ...] | None
    # 3.3.10. Customizing positional arguments in class pattern matching
    # SEE: https://docs.python.org/3/reference/datamodel.html#customizing-positional-arguments-in-class-pattern-matching
    "__match_args__",  # Final[tuple[str, ...]]
    # functools
    # SEE: https://docs.python.org/3/library/functools.html
    "__wrapped__",  # Callable[..., Any]
    # tracebacks
    # SEE: https://docs.python.org/3/library/traceback.html
    "__traceback__",  # TracebackType
    "__cause__",  # BaseException | None
    "__context__",  # BaseException | None
    "__suppress_context__",  # bool
    "__notes__",  # str
    # Generic Aliases
    # SEE: https://docs.python.org/3/library/stdtypes.html
    "__origin__",  # type
    "__args__",  # tuple[type, ...]
    "__parameters__",  # tuple[type, ...]
    "__unpacked__",  # bool
    "__typing_unpacked_tuple_args__",  # tuple[type, ...]
    # sys
    # SEE: https://docs.python.org/3/library/sys.html
    "__stdin__",  # TextIOWrapper
    "__stdout__",  # TextIOWrapper
    "__stderr__",  # TextIOWrapper
    # dataclasses
    # SEE: https://docs.python.org/3/library/dataclasses.html
    "__dataclass_fields__",  # dict[str, Field]
    # types
    # SEE: https://docs.python.org/3/library/types.html
    "__orig_bases__",  # tuple[type, ...]
    # weakref
    # SEE: https://docs.python.org/3/library/weakref.html
    "__weakref__",  # weakref
})
r"""Dunder attributes."""
