# python-no-builtin-eval

A modified version of the hook at <https://github.com/pre-commit/pygrep-hooks>.

- allows `<obj>.eval`, e.g. `pandas.eval`.
- only blank `eval(` and `builtins.eval(` are forbidden.
