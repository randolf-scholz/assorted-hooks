r"""Test check_no_hints_overload_implementation."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_typing import check_no_hints_overload_implementation


def test_no_hints_overload_implementation_true_negative() -> None:
    code = r"""
    @overload
    def foo(x: int) -> int | None: ...
    @overload
    def foo(x: str) -> str | None: ...
    def foo(x):
        return x

    def bar(x: int) -> int | None: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_hints_overload_implementation(tree, filename="test.py") == 0


def test_no_hints_overload_implementation_true_negative_class() -> None:
    code = r"""
    class X:
        @overload
        def foo(x: int) -> int | None: ...
        @overload
        def foo(x: str) -> str | None: ...
        def foo(x):
            return x

    def foo(x: int | str) -> int | str:
            return x

    def bar(x: int) -> int | None: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_hints_overload_implementation(tree, filename="test.py") == 0


def test_no_hints_overload_implementation_true_args() -> None:
    code = r"""
    @overload
    def foo(x: int) -> int | None: ...
    @overload
    def foo(x: str) -> str | None: ...
    def foo(x: int | str):
        return x

    def bar(x: int) -> int | None: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_hints_overload_implementation(tree, filename="test.py") == 1


def test_no_hints_overload_implementation_true_positive_return() -> None:
    code = r"""
    @overload
    def foo(x: int) -> int | None: ...
    @overload
    def foo(x: str) -> str | None: ...
    def foo(x) -> int | str | None:
        return x

    def bar(x: int) -> int | None: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_hints_overload_implementation(tree, filename="test.py") == 1
