#!/usr/bin/env python
r"""Checks for interaction with numpy."""

# 1. axes vs axis: we check that functions definitions use the spelling "axis" instead of axes,
#    even when the function is supposed to handle multiple axes.
# 2. Accidental cubic complexity due to use of trace:
#    Instead of using `np.trace(A.T @ B)`, use `np.einsum("ij,ji->", A, B)` or `np.tensordot(A, B)`.
# 3. Flag usage of `np.linalg.inv` and `np.linalg.pinv`: Use `np.linalg.solve` or `np.linalg.lstsq` instead,
#    Potentially with matrix factorization.
