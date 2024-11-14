r"""Base classes for AST-based hooks."""

__all__ = ["Violation"]

import ast
from abc import abstractmethod
from typing import ClassVar


class Violation:
    r"""Base class for violations."""

    CODE: ClassVar[str]
    r"""The violation code."""
    NAME: ClassVar[str]
    r"""The violation name."""
    node: ast.AST
    r"""The node that caused the violation."""
    lineno: int
    r"""The line number of the violation."""

    @abstractmethod
    def trigger(self, node: ast.AST, /) -> bool:
        r"""Trigger the violation."""
        ...

    @abstractmethod
    def check_disabled(self, node: ast.AST, /) -> bool:
        r"""Check if the violation is disabled.

        We look for comments like `# noqa: {self.CODE}`.
        """
        ...
