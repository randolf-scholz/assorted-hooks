r"""Provide type checked argument parsing.

Based on plain argparse, powered by dataclass_transform.
"""

__all__ = [
    # Types
    "Actions",
    # Functions
    "argument",
    "argparser",
    "make_parser",
    "parse_args",
]

from collections.abc import Container
from dataclasses import dataclass
from typing import Literal, TypeAlias, TypeVar, dataclass_transform

T = TypeVar("T")

Actions: TypeAlias = Literal[
    "store",
    "store_const",
    "store_true",
    "append",
    "append_const",
    "count",
    "help",
    "version",
]


@dataclass
class argument:
    r"""Wraps add_argument, similar to `dataclasses.field`."""

    action: Actions = NotImplemented  # pyright: ignore[reportAssignmentType]
    choices: Container = NotImplemented
    const: object = NotImplemented
    default: object = NotImplemented
    dest: str = NotImplemented
    help: str = NotImplemented
    metavar: str = NotImplemented
    nargs: int | Literal["?", "*", "+"] = NotImplemented
    required: bool = NotImplemented


@dataclass
class argparser:
    r"""Argument parser."""

    prog: str = NotImplemented
    usage: str = NotImplemented
    description: str = NotImplemented
    epilog: str = NotImplemented
    parents: list["argparser"] = NotImplemented
    formatter_class: str = NotImplemented
    prefix_chars: str = NotImplemented
    fromfile_prefix_chars: str = NotImplemented
    argument_default: object = NotImplemented
    conflict_handler: str = NotImplemented
    add_help: bool = NotImplemented
    allow_abbrev: bool = NotImplemented
    exit_on_error: bool = NotImplemented


def parse_args() -> None:
    r"""Parse the args."""


@dataclass_transform()
def make_parser(cls: type[T], /) -> type[T]:
    r"""Perform dataclass transform to create an argparser instance.

    This will do the following:
        - ClassVar Fields: description
        - Add a classmethod `parse_args` that creates an instance of the class,
          by parsing the options.

    Example:
        @make_parser
        class Options:



            fname: str = argument(
                help="One or multiple files, folders or file patterns.",
            )
            recursive: bool = argument(
                action="store_true",
                help="Recursively check for unions.",
            )
    """
    raise NotImplementedError(f"This is a dataclass transform, not a function. {cls=}")
