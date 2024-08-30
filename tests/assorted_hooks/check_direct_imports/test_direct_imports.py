r"""Test that direct imports are not used."""

import ast
from textwrap import dedent

from assorted_hooks.ast.check_direct_imports import check_direct_imports


def test_match_value_passes() -> None:
    code = r"""
    import builtins
    from builtins import str

    match "foo":
        case builtins.str:
             raise ValueError
    """
    tree = ast.parse(dedent(code))
    assert check_direct_imports(tree, "test.py") == 0


def test_import() -> None:
    code = r"""
    import builtins
    from builtins import str

    x = builtins.str('foo')
    """
    tree = ast.parse(dedent(code))
    assert check_direct_imports(tree, "test.py") == 1
