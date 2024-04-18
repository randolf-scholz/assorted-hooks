"""Tests for assorted_hooks.check_typing.check_overload_default_ellipsis."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_typing import check_overload_default_ellipsis


def test_overload_assign_positional_only():
    code = r"""
    @overload
    def foo(x: int, display: bool = True, /) -> int: ...
    @overload
    def foo(x: float, display: bool = True, /) -> float: ...
    def foo(x, display=True):
        if display:
            print(x)
        return x
    """
    tree = ast.parse(dedent(code))
    assert check_overload_default_ellipsis(tree, fname="test.py") == 2

    code = r"""
    @overload
    def foo(x: int, display: bool = ..., /) -> int: ...
    @overload
    def foo(x: float, display: bool = ..., /) -> float: ...
    def foo(x, display=True):
        if display:
            print(x)
        return x
    """
    tree = ast.parse(dedent(code))
    assert check_overload_default_ellipsis(tree, fname="test.py") == 0


def test_overload_assign_positional_or_keyword():
    code = r"""
    @overload
    def foo(x: int, display: bool = True) -> int: ...
    @overload
    def foo(x: float, display: bool = True) -> float: ...
    def foo(x, display=True):
        if display:
            print(x)
        return x
    """
    tree = ast.parse(dedent(code))
    assert check_overload_default_ellipsis(tree, fname="test.py") == 2

    code = r"""
    @overload
    def foo(x: int, display: bool = ...) -> int: ...
    @overload
    def foo(x: float, display: bool = ...) -> float: ...
    def foo(x, display=True):
        if display:
            print(x)
        return x
    """
    tree = ast.parse(dedent(code))
    assert check_overload_default_ellipsis(tree, fname="test.py") == 0


def test_overload_assign_keyword_only():
    code = r"""
    @overload
    def foo(x: int, *, display: bool = True) -> int: ...
    @overload
    def foo(x: float, *, display: bool = True) -> float: ...
    def foo(x, *, display=True):
        if display:
            print(x)
        return x
    """
    tree = ast.parse(dedent(code))
    assert check_overload_default_ellipsis(tree, fname="test.py") == 2

    code = r"""
    @overload
    def foo(x: int, *, display: bool = ...) -> int: ...
    @overload
    def foo(x: float, *, display: bool = ...) -> float: ...
    def foo(x, *, display=True):
        if display:
            print(x)
        return x
    """
    tree = ast.parse(dedent(code))
    assert check_overload_default_ellipsis(tree, fname="test.py") == 0
