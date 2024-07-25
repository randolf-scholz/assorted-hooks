r"""Tests for `ast_utils.py`."""

import ast

import pytest

from assorted_hooks.ast.ast_utils import (
    FunctionContextVisitor,
    yield_functions_in_context,
)

TEST_CASE_1 = r"""
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
EXPECTED_1 = [("__getitem__", 0, 2, "Foo"), ("__getitem__", 0, 2, "Bar")]

TEST_CASE_2 = r"""
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
EXPECTED_2 = [("fromkeys", 1, 2, "MyDict")]


TEST_CASES = [TEST_CASE_1, TEST_CASE_2]
EXPECTED = [EXPECTED_1, EXPECTED_2]
CASES = list(zip(TEST_CASES, EXPECTED, strict=True))


@pytest.mark.parametrize(("test_case", "expected"), CASES, ids=lambda _: "test")
def test_function_context_visitor(*, test_case: str, expected: list) -> None:
    tree = ast.parse(test_case)
    funcs = list(FunctionContextVisitor(tree))

    assert len(funcs) == len(expected)
    for ctx, (name, num_fn, num_overload, parent) in zip(funcs, expected, strict=True):
        assert ctx.name == name
        assert len(ctx.function_defs) == num_fn
        assert len(ctx.overload_defs) == num_overload
        assert getattr(ctx.context, "name", None) == parent


@pytest.mark.parametrize(("test_case", "expected"), CASES, ids=lambda _: "test")
def test_yield_functions_in_context(*, test_case: str, expected: list) -> None:
    tree = ast.parse(test_case)
    funcs = list(yield_functions_in_context(tree))

    assert len(funcs) == len(expected)
    for ctx, (name, num_fn, num_overload, parent) in zip(funcs, expected, strict=True):
        assert ctx.name == name
        assert len(ctx.function_defs) == num_fn
        assert len(ctx.overload_defs) == num_overload
        assert getattr(ctx.context, "name", None) == parent
