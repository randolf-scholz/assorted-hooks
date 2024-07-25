r"""Tests for `ast_utils.py`."""

import ast

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


def test_function_context_visitor():
    tree = ast.parse(TEST_CASE_1)
    funcs = list(FunctionContextVisitor(tree))
    assert len(funcs) == 2
    assert all(func[0] is None for func in funcs)
    assert all(len(func[1]) == 2 for func in funcs)


def test_yield_functions_in_context():
    tree = ast.parse(TEST_CASE_1)
    funcs = list(yield_functions_in_context(tree))
    assert len(funcs) == 2
    assert all(func[0] is None for func in funcs)
    assert all(len(func[1]) == 2 for func in funcs)
