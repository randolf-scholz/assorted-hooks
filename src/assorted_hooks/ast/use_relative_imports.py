r"""Rewrite absolute imports into relative ones for the current package."""

__all__ = [
    "check_file",
    "fix_absolute_imports",
    "get_candidates",
    "get_package_parts",
    "main",
]

import argparse
import ast
import logging
import sys
from copy import deepcopy
from pathlib import Path

from assorted_hooks.ast.ast_utils import patch_node
from assorted_hooks.utils import get_path_relative_to_git_root, get_python_files

__logger__ = logging.getLogger(__name__)


def get_package_parts(path: str | Path, /) -> tuple[str, ...]:
    r"""Return the dotted package path for a file based on ``__init__.py`` files."""
    current = Path(path).resolve().parent
    parts: list[str] = []

    while (current / "__init__.py").exists():
        parts.append(current.name)
        current = current.parent

    return tuple(reversed(parts))


def _relative_module_for_current_package(
    module: str, package_parts: tuple[str, ...], /
) -> str | None:
    r"""Return the relative module inside the current package, if any."""
    if not package_parts:
        return None

    module_parts = module.split(".")
    package_len = len(package_parts)

    for idx in range(len(module_parts) - package_len, -1, -1):
        if tuple(module_parts[idx : idx + package_len]) == package_parts:
            remainder = module_parts[idx + package_len :]
            return ".".join(remainder)

    return None


def fix_absolute_imports(
    lines: list[str], nodes: list[ast.ImportFrom], package_parts: tuple[str, ...], /
) -> list[str]:
    r"""Rewrite absolute imports to relative imports within the current package."""
    patched_lines = deepcopy(lines)

    for node in sorted(nodes, key=lambda n: (n.lineno, n.col_offset), reverse=True):
        if node.module is None or node.level != 0:
            continue

        relative_module = _relative_module_for_current_package(
            node.module, package_parts
        )
        if relative_module is None:
            continue

        new_node = deepcopy(node)
        new_node.level = 1
        new_node.module = relative_module or None
        patched_lines = patch_node(patched_lines, node, new_node)

    return patched_lines


def get_candidates(
    tree: ast.AST, package_parts: tuple[str, ...], /
) -> list[ast.ImportFrom]:
    r"""Return absolute imports that can be rewritten for the current package."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module is not None
        and _relative_module_for_current_package(node.module, package_parts) is not None
    ]


def check_file(filepath: str | Path, /, *, fix: bool = False) -> int:
    r"""Check or rewrite absolute imports for the current package in a file."""
    path = Path(filepath)
    filename = str(get_path_relative_to_git_root(path))
    package_parts = get_package_parts(path)
    if not package_parts:
        return 0

    original = path.read_text(encoding="utf8")
    tree = ast.parse(original, filename=filename)
    candidates = get_candidates(tree, package_parts)

    if not candidates:
        return 0

    for node in candidates:
        print(
            f"{filename}:{node.lineno}:"
            " absolute import within the current package should be relative"
        )

    if not fix:
        return len(candidates)

    new_lines = fix_absolute_imports(
        original.splitlines(keepends=True), candidates, package_parts
    )
    new_text = "".join(new_lines)

    if new_text == original:
        return 0

    path.write_text(new_text, encoding="utf8")

    for node in candidates:
        __logger__.info('Rewrote "%s:%s"', filename, node.lineno)

    return len(candidates)


def main() -> None:
    r"""Main program."""
    parser = argparse.ArgumentParser(
        description="Rewrite absolute imports into relative ones for the current package.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=str,
        help="One or multiple files, folders or file patterns.",
    )
    parser.add_argument(
        "--fix",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Rewrite the affected imports in-place.",
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Print debug information.",
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        __logger__.debug("args: %s", vars(args))

    files: list[Path] = get_python_files(args.files)
    violations = 0

    for file in files:
        __logger__.debug('Checking "%s:0"', file)
        try:
            violations += check_file(file, fix=args.fix)
        except Exception as exc:
            raise RuntimeError(f"{file!s}: Rewriting file failed!") from exc

    if violations:
        action = "Rewrote" if args.fix else "Found"
        subject = f"{violations} imports." if args.fix else f"{violations} violations."
        print(f"{'-' * 79}\n{action} {subject}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
