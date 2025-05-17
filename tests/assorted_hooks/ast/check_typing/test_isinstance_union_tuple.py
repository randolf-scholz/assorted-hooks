r"""Test that isinstance and issubclass are not used with tuple or Union."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_typing import (
    check_no_tuple_isinstance,
    check_no_union_isinstance,
)


def test_no_tuple_isinstance() -> None:
    code = r"""
    isinstance(x, tuple)
    """
    tree = ast.parse(dedent(code))
    assert check_no_tuple_isinstance(tree, fname="test.py") == 0

    code = r"""
    isinstance(x, ())
    """
    tree = ast.parse(dedent(code))
    assert check_no_tuple_isinstance(tree, fname="test.py") == 1

    code = r"""
    isinstance(x, (int,))
    """
    tree = ast.parse(dedent(code))
    assert check_no_tuple_isinstance(tree, fname="test.py") == 1

    code = r"""
    isinstance(x, (tuple, list))
    """
    tree = ast.parse(dedent(code))
    assert check_no_tuple_isinstance(tree, fname="test.py") == 1


def test_no_tuple_issubclass() -> None:
    code = r"""
    issubclass(x, tuple)
    """
    tree = ast.parse(dedent(code))
    assert check_no_tuple_isinstance(tree, fname="test.py") == 0

    code = r"""
    issubclass(x, ())
    """
    tree = ast.parse(dedent(code))
    assert check_no_tuple_isinstance(tree, fname="test.py") == 1

    code = r"""
    issubclass(x, (int,))
    """
    tree = ast.parse(dedent(code))
    assert check_no_tuple_isinstance(tree, fname="test.py") == 1

    code = r"""
    issubclass(x, (tuple, list))
    """
    tree = ast.parse(dedent(code))
    assert check_no_tuple_isinstance(tree, fname="test.py") == 1


def test_no_union_isinstance() -> None:
    code = r"""
    isinstance(x, tuple)
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 0

    code = r"""
    isinstance(x, ())
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 0

    code = r"""
    isinstance(x, Union[int])
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 1

    code = r"""
    isinstance(x, tuple | list)
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 1

    code = r"""
    isinstance(x, Union[tuple, list])
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 1


def test_no_union_issubclass() -> None:
    code = r"""
    issubclass(x, tuple)
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 0

    code = r"""
    issubclass(x, ())
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 0

    code = r"""
    issubclass(x, Union[int])
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 1

    code = r"""
    issubclass(x, tuple | list)
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 1, ast.dump(
        tree, indent=4
    )

    code = r"""
    issubclass(x, Union[tuple, list])
    """
    tree = ast.parse(dedent(code))
    assert check_no_union_isinstance(tree, fname="test.py") == 1
