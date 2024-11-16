# pyright-concise

Wrapper for `pyright` with concise output formatting. This produces a concise output similar to `mypy --no-pretty --no-error-summary --hide-error-end --hide-error-context`.

- prints exactly one line per error
- always includes the error code
- shortens file paths relative to the current working directory
- adds summary at the end of the output
