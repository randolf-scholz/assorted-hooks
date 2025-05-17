r"""Tests for assorted_hooks.check_typing.check_pep604_union."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_typing import check_pep604_union


def test_pep604_union() -> None:
    code = r"""
    def foo(x: int) -> int | None: ...
    """
    tree = ast.parse(dedent(code))
    assert check_pep604_union(tree, filename="test.py") == 0

    code = r"""
    def foo(x: int) -> Union[None | int]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_pep604_union(tree, filename="test.py") == 1

    code = r"""
    def foo(x: int) -> list[Union[int, None]]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_pep604_union(tree, filename="test.py") == 1

    code = r"""
    def foo(x: int) -> list[None | int]: ...
    """
    tree = ast.parse(dedent(code))
    assert check_pep604_union(tree, filename="test.py") == 0
