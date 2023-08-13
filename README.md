# custom pre-commit hooks

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## imported-attributes

This hook checks that if both a module is imported and some class/function from that module, always the directly imported symbol is used.

```python
import collections.abc as abc
from collections.abc import Sequence

def foo(x: Sequence) -> Sequence:
    assert isinstance(x, abc.Sequence)  # <- use Sequence instead of abc.Sequence
    return x
```

## jupyter-clear-output

This hook clears the output of jupyter notebooks. This is useful to avoid large diffs in commits. Use the `files` 
and `exclude` configuration options to specify which notebooks should be spared.
