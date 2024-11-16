
# python-no-blanket-type-ignore

A modified version of the hook at <https://github.com/pre-commit/pygrep-hooks>.

- colon after "type" non-optional.
- also checks for `pyright: ignore` comments
- To ignore errors across a whole file, use `# mypy: ignore-errors` instead.
  - <https://mypy.readthedocs.io/en/stable/common_issues.html#ignoring-a-whole-file>
  - <https://microsoft.github.io/pyright/#/comments?id=comments>
