r"""AST based utilities for the assorted_hooks package."""

__all__ = [
    # Types
    "Func",
    # Functions
    "get_full_attribute_name",
    "is_overload",
    "is_staticmethod",
    "is_dunder_method",
    "is_private_method",
    "is_decorated_with",
    # yield functions (Iterators)
    "yield_functions",
    "yield_classes",
    "yield_funcs_in_classes",
    "yield_funcs_outside_classes",
]

import ast
from ast import AST, AsyncFunctionDef, Attribute, Call, ClassDef, FunctionDef, Name
from collections.abc import Iterator
from typing import TypeAlias

Func: TypeAlias = FunctionDef | AsyncFunctionDef
# type Func = FunctionDef | AsyncFunctionDef
r"""Type alias for function-defs."""


def is_overload(node: Func, /) -> bool:
    r"""Checks if the func is an overload."""
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "overload" in [d.id for d in decorators]


def is_staticmethod(node: Func, /) -> bool:
    r"""Checks if the func is a staticmethod."""
    decorators = (d for d in node.decorator_list if isinstance(d, Name))
    return "staticmethod" in [d.id for d in decorators]


def is_dunder_method(node: Func, /) -> bool:
    r"""Checks if the name is a dunder name."""
    name = node.name
    return name.startswith("__") and name.endswith("__") and name.isidentifier()


def is_private_method(node: Func, /) -> bool:
    r"""Checks if the name is a private name."""
    name = node.name
    return name.startswith("_") and not name.startswith("__") and name.isidentifier()


def is_decorated_with(node: Func, name: str, /) -> bool:
    r"""Checks if the function is decorated with a certain decorator."""
    return name in (get_full_attribute_name(d) for d in node.decorator_list)


def get_full_attribute_name(node: AST, /) -> str:
    r"""Get the parent of an attribute node."""
    match node:
        case Call(func=Attribute() | Name() as func):
            return get_full_attribute_name(func)
        case Attribute(value=Attribute() | Name() as value, attr=attr):
            string = get_full_attribute_name(value)
            return f"{string}.{attr}"
        case Name(id=node_id):
            return node_id
        case _:
            raise TypeError(f"Expected Call, Attribute or Name, got {type(node)=!r}")


def yield_functions(tree: AST, /) -> Iterator[Func]:
    r"""Get all function-defs from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, Func):
            yield node


def yield_classes(tree: AST, /) -> Iterator[ClassDef]:
    r"""Get all class-defs from the tree."""
    for node in ast.walk(tree):
        if isinstance(node, ClassDef):
            yield node


def yield_funcs_in_classes(tree: AST, /) -> Iterator[Func]:
    r"""Get all function that are defined directly inside class bodies."""
    for cls in yield_classes(tree):
        for node in cls.body:
            if isinstance(node, Func):
                yield node


def yield_funcs_outside_classes(tree: AST, /) -> Iterator[Func]:
    r"""Get all functions that are nod defined inside class body."""
    funcs_in_classes: set[AST] = set()

    for node in ast.walk(tree):
        match node:
            case ClassDef(body=body):
                funcs_in_classes.update(
                    child for child in body if isinstance(child, Func)
                )
            # FIXME: https://github.com/python/cpython/issues/106246
            case FunctionDef() | AsyncFunctionDef():
                if node not in funcs_in_classes:
                    yield node
