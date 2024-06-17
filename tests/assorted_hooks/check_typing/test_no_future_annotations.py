r"""Test that __future__ import annotations is not used."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_typing import check_no_future_annotations


def test_no_future_annotations():
    code = r"""
    from __future__ import annotations
    """
    tree = ast.parse(dedent(code))
    assert check_no_future_annotations(tree, fname="test.py") == 1

    code = r"""
    from __future__ import foo
    """
    tree = ast.parse(dedent(code))
    assert check_no_future_annotations(tree, fname="test.py") == 0

    code = r"""
    from __future__ import foo, annotations
    """
    tree = ast.parse(dedent(code))
    assert check_no_future_annotations(tree, fname="test.py") == 1
