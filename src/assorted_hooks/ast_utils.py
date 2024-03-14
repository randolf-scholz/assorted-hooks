"""AST based utilities for the assorted_hooks package."""

__all__ = [
    # Types
    "Func",
    # Functions
    "is_overload",
    "is_staticmethod",
    "is_dunder",
    "is_private",
    "is_decorated_with",
]

from ast import AsyncFunctionDef, FunctionDef, Name
from typing import TypeAlias

Func: TypeAlias = FunctionDef | AsyncFunctionDef
r"""Type alias for function-defs."""


def is_overload(node: Func, /) -> bool:
    r"""Checks if the func is an overload."""
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "overload" in [d.id for d in decorators]


def is_staticmethod(node: Func, /) -> bool:
    r"""Checks if the func is a staticmethod."""
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "staticmethod" in [d.id for d in decorators]


def is_dunder(node: Func, /) -> bool:
    r"""Checks if the name is a dunder name."""
    name = node.name
    return name.startswith("__") and name.endswith("__") and name.isidentifier()


def is_private(node: Func, /) -> bool:
    r"""Checks if the name is a private name."""
    name = node.name
    return name.startswith("_") and not name.startswith("__") and name.isidentifier()


def is_decorated_with(node: Func, name: str, /) -> bool:
    r"""Checks if the function is decorated with a certain decorator."""
    return name in [get_full_attribute_name(d) for d in node.decorator_list]
