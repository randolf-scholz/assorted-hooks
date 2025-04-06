r"""Test the check_runtime_data_protocol function."""

import ast

import pytest

from assorted_hooks.ast.check_runtime_data_protocol import check_runtime_data_protocol

EXAMPLE = """
@runtime_checkable
class MyDataProtocol(Protocol):
    x: float
    y: float
"""

NON_EXAMPLE = """
@runtime_checkable
class MyProtocol(Protocol):
    def foo(self) -> None: ...
"""


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        (EXAMPLE, 1),
        (NON_EXAMPLE, 0),
        ("", 0),
        ("class MyProto(Protocol): ...", 0),
        ("@runtime_checkable\nclass MyClass(Protocol): ...", 0),
    ],
)
def test_is_runtime_data_protocol(*, case: str, expected: int) -> None:
    r"""Test the is_runtime_data_protocol function."""
    # Parse the example code into an AST
    tree = ast.parse(case)

    # Check if the class is a runtime data protocol
    result = check_runtime_data_protocol(tree, "test")

    # Assert that the result matches the expected value
    assert result == expected
