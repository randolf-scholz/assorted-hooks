"""Tests for assorted_hooks.check_typing.check_no_return_union."""

import ast
from textwrap import dedent

from assorted_hooks.check_typing import check_typealias_union


def test_typealias_union():
    code = r"""
    Number: TypeAlias = int | float
    """
    tree = ast.parse(dedent(code))
    assert check_typealias_union(tree, fname="test.py") == 1


def test_typealias_union_false():
    code = r"""
    Number: UnionType = int | float
    """
    tree = ast.parse(dedent(code))
    assert check_typealias_union(tree, fname="test.py") == 0


def test_typealias_union_large():
    code = r"""
    LazySpec: TypeAlias = (
        LazyValue[T]  # lazy value
        | Callable[[], T]  # no args
        | Callable[[Any], T]  # single arg
        | tuple[Callable[..., T], tuple]  # args
        | tuple[Callable[..., T], dict]  # kwargs
        | tuple[Callable[..., T], tuple, dict]  # args, kwargs
        | T  # direct value
    )
    """
    tree = ast.parse(dedent(code))
    assert check_typealias_union(tree, fname="test.py") == 1
