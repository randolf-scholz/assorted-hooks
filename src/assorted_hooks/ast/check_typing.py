#!/usr/bin/env python
r"""Disallow mixed positional and keyword arguments in function-defs."""

__all__ = [
    # Functions
    "check_file",
    "check_concrete_classes_concrete_types",
    "check_no_future_annotations",
    "check_no_hints_overload_implementation",
    "check_no_optional",
    "check_no_return_union",
    "check_no_tuple_isinstance",
    "check_no_union_isinstance",
    "check_optional",
    "check_overload_default_ellipsis",
    "check_pep604_union",
    "get_python_files",
    "main",
]

import argparse
import ast
import builtins
import logging
import sys
from ast import (
    AST,
    AnnAssign,
    AsyncFunctionDef,
    BinOp,
    BitOr,
    Call,
    ClassDef,
    Constant,
    FunctionDef,
    ImportFrom,
    Module,
    Name,
    Subscript,
    Tuple,
)
from pathlib import Path

from assorted_hooks.ast.ast_utils import (
    Func,
    OverloadVisitor,
    has_union,
    is_protocol,
    is_typing_union,
    is_union,
    yield_concrete_classes,
    yield_namespace_and_funcs,
    yield_overloads,
)
from assorted_hooks.utils import get_python_files

__logger__ = logging.getLogger(__name__)


def check_no_future_annotations(tree: AST, /, *, filename: str) -> int:
    r"""Make sure PEP563 is not used."""
    violations = 0
    for node in ast.walk(tree):
        match node:
            # FIXME: https://github.com/python/cpython/issues/107497
            case ImportFrom(module="__future__") as future_import:
                for alias in future_import.names:
                    if alias.name == "annotations":
                        violations += 1
                        print(f"{filename}:{node.lineno}: Do not use PEP563!")
    return violations


def check_overload_default_ellipsis(tree: AST, /, *, filename: str) -> int:
    r"""Check that keyword arguments in overloads assign Ellipsis instead of a value."""
    violations = 0

    for node in yield_overloads(tree):
        pos_defaults = node.args.defaults
        pos_args = node.args.posonlyargs + node.args.args
        pos_args = pos_args[-len(pos_defaults) :] if pos_defaults else []
        for arg, default in zip(pos_args, pos_defaults, strict=True):
            match default:
                case Constant(value=builtins.Ellipsis):
                    continue
                case _:
                    violations += 1
                    print(
                        f"{filename}:{node.lineno}: Default value for"
                        f" {arg.arg!r} inside @overload should be '...'"
                    )

        kw_args = [] if node.args.kwonlyargs is None else node.args.kwonlyargs
        kw_defaults = [] if node.args.kw_defaults is None else node.args.kw_defaults

        for kwarg, kw_default in zip(kw_args, kw_defaults, strict=True):
            match kw_default:
                case None | Constant(value=builtins.Ellipsis):
                    continue
                case _:
                    violations += 1
                    print(
                        f"{filename}:{node.lineno}: Default value for"
                        f" {kwarg.arg!r} inside @overload should be '...'"
                    )
    return violations


def check_pep604_union(tree: AST, /, *, filename: str) -> int:
    r"""Check that X | Y is used instead of Union[X, Y]."""
    violations = 0

    for node in ast.walk(tree):
        if is_typing_union(node):
            violations += 1
            print(f"{filename}:{node.lineno}: Use X | Y instead of Union[X, Y]!")

    return violations


def check_no_return_union(
    tree: AST,
    /,
    *,
    recursive: bool,
    filename: str,
    include_overload_implementation: bool = False,
    include_protocols: bool = True,
) -> int:
    r"""Check if function returns a union type.

    By default, for overloaded functions only the overloads are checked and not the implementations.

    Args:
        tree (AST): The AST to check.
        recursive (bool): If True, check recursively for unions.
        filename (str): The name of the file being checked.
        include_overload_implementation (bool): If True, include the implementation of overloads in the check.
        include_protocols (bool): If True, exclude protocol classes from the check.
    """
    violations = 0

    # determine all functions to check
    funcs: list[Func] = []

    for fn_ctx in OverloadVisitor(tree):
        # skip if inside protocol context.
        if (
            not include_protocols
            and isinstance(fn_ctx.context, ClassDef)
            and any(is_protocol(base) for base in fn_ctx.context.bases)
        ):
            continue

        # always include overload definitions
        funcs += fn_ctx.overloads

        if (fn_ctx.implementation is not None) and (
            not fn_ctx.overloads or include_overload_implementation
        ):
            # include implementation if it is not an overload
            # or if we want to include the implementation
            funcs.append(fn_ctx.implementation)

    # emit violations
    for fn in funcs:
        if fn.returns is None:
            continue
        if is_union(fn.returns) or (recursive and has_union(fn.returns)):
            violations += 1
            print(f"{filename}:{fn.lineno}: Avoid returning union types!")

    return violations


def check_no_optional(tree: AST, /, *, filename: str) -> int:
    r"""Check that `None | T` is used instead of `Optional[T]`."""
    violations = 0

    for node in ast.walk(tree):
        match node:
            case Subscript(value=Name(id="Optional")):
                violations += 1
                print(f"{filename}:{node.lineno}: Use None | X instead of Optional[X]")

    return violations


def check_no_union_isinstance(tree: AST, /, *, filename: str) -> int:
    r"""Checks that tuples are used instead of unions in isinstance checks."""
    violations = 0

    for node in ast.walk(tree):
        match node:
            case Call(
                func=Name(id="isinstance"),
                args=[_, BinOp(op=BitOr()) | Subscript(value=Name(id="Union"))],
            ):
                violations += 1
                print(
                    f"{filename}:{node.lineno}: Use tuple instead of union in isinstance"
                )
            case Call(
                func=Name(id="issubclass"),
                args=[_, BinOp(op=BitOr()) | Subscript(value=Name(id="Union"))],
            ):
                violations += 1
                print(
                    f"{filename}:{node.lineno}: Use tuple instead of union in issubclass"
                )

    return violations


def check_no_tuple_isinstance(tree: AST, /, *, filename: str) -> int:
    r"""Checks that unions are used instead of tuples in isinstance checks."""
    violations = 0

    for node in ast.walk(tree):
        match node:
            case Call(
                func=Name(id="isinstance"),
                args=[_, Tuple() | Subscript(value=Name(id="tuple"))],
            ):
                violations += 1
                print(
                    f"{filename}:{node.lineno}: Use union instead of tuple in isinstance"
                )
            case Call(
                func=Name(id="issubclass"),
                args=[_, Tuple() | Subscript(value=Name(id="tuple"))],
            ):
                violations += 1
                print(
                    f"{filename}:{node.lineno}: Use union instead of tuple in issubclass"
                )

    return violations


def check_concrete_classes_concrete_types(
    tree: AST,
    /,
    *,
    filename: str,
    check_attrs: bool = False,
    check_funcs: bool = True,
    values: frozenset[str] = frozenset({
        "AbstractSet",
        "Collection",
        "Iterable",
        "Mapping",
        "MutableMapping",
        "MutableSequence",
        "MutableSet",
        "Sequence",
        "Set",
        "Sized",
    }),
) -> int:
    r"""Check that concrete classes use concrete return types."""
    # These generic types are considered non-concrete.
    # Better would be to use a type checker and see if ABCs/Protocols are returned.
    violations = 0
    matches: list[AnnAssign | FunctionDef | AsyncFunctionDef] = []

    for cls in yield_concrete_classes(tree):
        for node in cls.body:
            match node:
                case AnnAssign(annotation=Subscript(value=Name(id=ann))) if check_attrs:
                    if ann in values:
                        matches.append(node)
                case FunctionDef(returns=Subscript(value=Name(id=ann))) if check_funcs:
                    if ann in values:
                        matches.append(node)
                case AsyncFunctionDef(returns=Subscript(value=Name(id=ann))) if (
                    check_funcs
                ):
                    if ann in values:
                        matches.append(node)

    for node in matches:
        violations += 1
        print(
            f"{filename}:{node.lineno}: Concrete classes should return concrete types."
        )

    return violations


def check_no_hints_overload_implementation(
    tree: ClassDef | Module, /, *, filename: str
) -> int:
    r"""Checks that the implementation of an overloaded function has no type hints."""
    violations = 0
    namespace_and_funcs: list[tuple[tuple[str, ...], Func]] = list(
        yield_namespace_and_funcs(tree)
    )
    namespaces = {namespace for namespace, _ in namespace_and_funcs}

    # group by namespace, collect values in list
    grouped_funcs = {
        namespace: [func for name, func in namespace_and_funcs if name == namespace]
        for namespace in namespaces
    }

    for funcs in grouped_funcs.values():
        # NOTE: we assume overloads are defined before implementations.
        overloaded_funcs: set[str] = set()
        for node in funcs:
            match node:
                case (
                    (
                        FunctionDef(decorator_list=[Name(id="overload"), *_])
                        | AsyncFunctionDef(decorator_list=[Name(id="overload"), *_])
                    ) as func
                ):
                    overloaded_funcs.add(func.name)
                case func if func.name in overloaded_funcs:
                    if (
                        any(arg.annotation is not None for arg in func.args.args)
                        or func.returns is not None
                    ):
                        violations += 1
                        print(
                            f"{filename}:{func.lineno}: Overloaded function"
                            f" implementation {func.name!r} should not have type hints."
                        )
    return violations


def check_optional(tree: AST, /, *, filename: str) -> int:
    r"""Check that `Optional[T]` is used instead of `None | T`."""
    violations = 0

    for node in ast.walk(tree):
        match node:
            case BinOp(op=BitOr(), left=Constant(value=None)):
                violations += 1
                print(f"{filename}:{node.lineno}: Use Optional[X] instead of None | X")
            case BinOp(op=BitOr(), right=Constant(value=None)):
                violations += 1
                print(f"{filename}:{node.lineno}: Use Optional[X] instead of X | None")

    return violations


def check_file(filepath: str | Path, /, *, options: argparse.Namespace) -> int:
    r"""Check whether the file contains mixed positional and keyword arguments."""
    # Get the AST
    violations = 0
    path = Path(filepath)
    filename = str(
        path if not path.is_relative_to(Path.cwd()) else path.relative_to(Path.cwd())
    )
    text = path.read_text(encoding="utf8")
    tree = ast.parse(text, filename=filename)

    if options.check_optional:
        violations += check_optional(tree, filename=filename)
    if options.check_no_optional:
        violations += check_no_optional(tree, filename=filename)
    if options.check_pep604_union:
        violations += check_pep604_union(tree, filename=filename)
    if options.check_overload_default_ellipsis:
        violations += check_overload_default_ellipsis(tree, filename=filename)
    if options.check_no_future_annotations:
        violations += check_no_future_annotations(tree, filename=filename)
    if options.check_no_return_union:
        violations += check_no_return_union(
            tree,
            filename=filename,
            recursive=options.check_no_return_union_recursive,
            include_protocols=options.check_no_return_union_protocol,
        )
    if options.check_no_tuple_isinstance:
        violations += check_no_tuple_isinstance(tree, filename=filename)
    if options.check_no_union_isinstance:
        violations += check_no_union_isinstance(tree, filename=filename)
    if options.check_no_hints_overload_implementation:
        violations += check_no_hints_overload_implementation(tree, filename=filename)
    if options.check_concrete:
        violations += check_concrete_classes_concrete_types(tree, filename=filename)
    return violations


def main() -> None:
    r"""Main program."""
    parser = argparse.ArgumentParser(
        description="Check for disallowing positional_or_keyword arguments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    # region auto-enabled checks -------------------------------------------------------
    parser.add_argument(
        "--check-overload-default-ellipsis",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Check that in overloads Ellipsis is used as default value.",
    )
    parser.add_argument(
        "--check-pep604-union",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Check that `X | Y` is used instead of `Union[X, Y]`.",
    )
    parser.add_argument(
        "--check-no-future-annotations",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=True,
        help="Check that `from __future__ import annotations` is not used.",
    )
    # endregion auto-enabled checks ----------------------------------------------------
    # region auto-disabled checks ------------------------------------------------------
    parser.add_argument(
        "--check-no-optional",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that `T | None` is not used instead of `Optional[T]`.",
    )
    parser.add_argument(
        "--check-optional",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that `Optional[T]` is used instead of `T | None`.",
    )
    parser.add_argument(
        "--check-no-return-union",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that functions do not return Unions.",
    )
    parser.add_argument(
        "--check-no-return-union-recursive",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Recursively check that functions do not return Unions.",
    )
    parser.add_argument(
        "--check-concrete",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that concrete classes return concrete types.",
    )
    parser.add_argument(
        "--check-no-return-union-protocol",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that functions do not return Unions inside protocols.",
    )
    parser.add_argument(
        "--check-no-hints-overload-implementation",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that overloaded function implementations have no type hints.",
    )
    parser.add_argument(
        "--check-no-tuple-isinstance",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that isinstance uses union instead of tuples.",
    )
    parser.add_argument(
        "--check-no-union-isinstance",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Check that isinstance uses tuples instead of unions.",
    )
    # endregion auto-disabled checks ---------------------------------------------------
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        type=bool,
        default=False,
        help="Print debug information.",
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        __logger__.debug("args: %s", vars(args))

    # find all files
    files: list[Path] = get_python_files(args.files)

    # apply script to all files
    violations = 0
    exceptions = {}
    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            violations += check_file(file, options=args)
        except Exception as exc:  # noqa: BLE001
            exceptions[file] = exc
    if exceptions:
        msg = "\n".join(f"{key}: {value}" for key, value in exceptions.items())
        print(f"{'-' * 79}\nChecking the following files failed!\n{msg}")

    if violations:
        print(f"{'-' * 79}\nFound {violations} violations.")

    if violations or exceptions:
        raise SystemExit(1)
