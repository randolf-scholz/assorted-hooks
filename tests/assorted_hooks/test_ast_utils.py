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
    assert all(len(ctx.function_defs) == 0 for ctx in funcs)
    assert all(len(ctx.overload_defs) == 2 for ctx in funcs)


def test_yield_functions_in_context():
    tree = ast.parse(TEST_CASE_1)
    funcs = list(yield_functions_in_context(tree))
    assert len(funcs) == 2
    assert all(len(ctx.function_defs) == 0 for ctx in funcs)
    assert all(len(ctx.overload_defs) == 2 for ctx in funcs)
