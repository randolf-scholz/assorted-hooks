r"""Tests for `ast_utils.py`."""

import ast
from typing import NamedTuple

import pytest

from assorted_hooks.ast.ast_utils import (
    OverloadVisitor,
    yield_overloads_and_context,
)


class Expected(NamedTuple):
    r"""Expected result for a test case."""

    name: str
    ctx_name: str | None
    num_overloads: int
    has_implementation: bool


TEST_OVERLOAD_OTHER_CTX = r"""
class Foo:
    @overload
    def __getitem__(self, index: int) -> int: ...
    @overload
    def __getitem__(self, index: slice) -> str: ...

class Bar:
    @overload
    def __getitem__(self, index: int) -> int: ...
    @overload
    def __getitem__(self, index: slice) -> str: ...
r"""
RESULT_OVERLOAD_OTHER_CTX: list[Expected] = [
    Expected("__getitem__", "Foo", num_overloads=2, has_implementation=False),
    Expected("__getitem__", "Bar", num_overloads=2, has_implementation=False),
]

TEST_OVERLOAD_CLASSMETHOD = r"""
class MyDict:
    @classmethod
    @overload
    def fromkeys(cls, iterable: Iterable[K], value: None = ..., /) -> "MyDict[K, Any | None]": ...
    @classmethod
    @overload
    def fromkeys(cls, iterable: Iterable[K], value: V, /) -> "MyDict[K, V]": ...
    @classmethod
    def fromkeys(cls, iterable, value=None):
        return cls(super().fromkeys(iterable, value))
"""
RESULT_OVERLOAD_CLASSMETHOD: list[Expected] = [
    Expected("fromkeys", "MyDict", num_overloads=2, has_implementation=True),
]


TEST_SAME_NAME_AND_CTX = r"""
def foo(): ...
def foo(): ...
"""
RESULT_SAME_NAME_AND_CTX: list[Expected] = [
    Expected("foo", None, num_overloads=0, has_implementation=True),
    Expected("foo", None, num_overloads=0, has_implementation=True),
]

TEST_SAME_NAME_OTHER_CXT = r"""
def foo(): ...
class Bar:
    def foo(): ...
"""  # same name in different contexts
RESULT_SAME_NAME_OTHER_CTX: list[Expected] = [
    Expected("foo", None, num_overloads=0, has_implementation=True),
    Expected("foo", "Bar", num_overloads=0, has_implementation=True),
]

TEST_CXT_2 = r"""
class Foo:
    if TYPE_CHECKING:
        def foo(): ...
"""
RESULT_CXT_2: list[Expected] = [
    Expected("foo", "Foo", num_overloads=0, has_implementation=True),
]


TEST_ORDER = r"""
@overload
def foo(): ...
@overload
def foo(): ...

@overload
def baz(): ...
@overload
def baz(): ...

def qux(): ...

class Bar:
    def foo(): ...

@overload
def foo(): ...
def foo(): ...
"""
RESULT_ORDER: list[Expected] = [
    Expected("qux", None, num_overloads=0, has_implementation=True),
    Expected("foo", "Bar", num_overloads=0, has_implementation=True),
    Expected("foo", None, num_overloads=3, has_implementation=True),
    Expected("baz", None, num_overloads=2, has_implementation=False),
]

CASES = {
    "overload_other_ctx": (TEST_OVERLOAD_OTHER_CTX, RESULT_OVERLOAD_OTHER_CTX),
    "overload_classmethod": (TEST_OVERLOAD_CLASSMETHOD, RESULT_OVERLOAD_CLASSMETHOD),
    "same_name_and_ctx": (TEST_SAME_NAME_AND_CTX, RESULT_SAME_NAME_AND_CTX),
    "same_name_other_ctx": (TEST_SAME_NAME_OTHER_CXT, RESULT_SAME_NAME_OTHER_CTX),
    "order": (TEST_ORDER, RESULT_ORDER),
    "cxt_2": (TEST_CXT_2, RESULT_CXT_2),
}


@pytest.mark.parametrize("case", CASES)
def test_function_context_visitor(case: str) -> None:
    test_case, expected = CASES[case]
    tree = ast.parse(test_case)
    result = list(OverloadVisitor(tree))

    assert len(result) == len(expected)
    for ctx, expected_ctx in zip(result, expected, strict=True):
        assert ctx.name == expected_ctx.name
        assert (ctx.implementation is not None) is expected_ctx.has_implementation
        assert len(ctx.overloads) == expected_ctx.num_overloads
        assert getattr(ctx.context, "name", None) == expected_ctx.ctx_name


@pytest.mark.parametrize("case", CASES)
def test_yield_functions_in_context(case: str) -> None:
    test_case, expected = CASES[case]
    tree = ast.parse(test_case)
    result = list(yield_overloads_and_context(tree))

    assert len(result) == len(expected)
    for ctx, expected_ctx in zip(result, expected, strict=True):
        assert ctx.name == expected_ctx.name
        assert (ctx.implementation is not None) is expected_ctx.has_implementation
        assert len(ctx.overloads) == expected_ctx.num_overloads
        assert getattr(ctx.context, "name", None) == expected_ctx.ctx_name
