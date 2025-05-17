r"""Tests for assorted_hooks.check_typing.check_optional."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_typing import check_no_optional, check_optional


def test_optional() -> None:
    code = r"""
    def foo(x: int) -> int | None: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_optional(tree, fname="test.py") == 0
    assert check_optional(tree, fname="test.py") == 1

    code = r"""
    def foo(x: int) -> list[int | None]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_optional(tree, fname="test.py") == 0
    assert check_optional(tree, fname="test.py") == 1

    code = r"""
    def foo(x: int) -> Optional[int]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_optional(tree, fname="test.py") == 1
    assert check_optional(tree, fname="test.py") == 0

    code = r"""
    def foo(x: int) -> list[Optional[int]]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_no_optional(tree, fname="test.py") == 1
    assert check_optional(tree, fname="test.py") == 0
