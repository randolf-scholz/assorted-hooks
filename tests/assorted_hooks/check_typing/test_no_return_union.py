"""Tests for assorted_hooks.check_typing.check_no_return_union."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_typing import check_no_return_union


def test_no_return_union_pep604():
    code = r"""
    def foo(x: int) -> int | None: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, fname="test.py") == 1
    assert check_no_return_union(tree, recursive=True, fname="test.py") == 1


def test_no_return_union_pep604_recursion():
    code = r"""
    def foo(x: int) -> list[None | int]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, fname="test.py") == 0
    assert check_no_return_union(tree, recursive=True, fname="test.py") == 1


def test_no_return_union_typing_recursion():
    code = r"""
    def foo(x: int) -> list[Union[None, int]]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, fname="test.py") == 0
    assert check_no_return_union(tree, recursive=True, fname="test.py") == 1


def test_no_return_union_typing():
    code = r"""
    def foo(x: int) -> Union[int, None]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_return_union(tree, recursive=False, fname="test.py") == 1
    assert check_no_return_union(tree, recursive=True, fname="test.py") == 1
