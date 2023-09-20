#!/usr/bin/env python
"""Check triple quoted string finder."""
# # fmt: off
#
# def fp1():
#     f"""False Positive."""
#
#
# def fp2():
#     r"""False Positive."""
#
# r"""False Positive."""
#
# fp3 = r"""False Positive."""
# # fmt: on
#
# # ((?<=[:\n]\n)\s*"""|(?<=\()\s*"""|(?:^#[^\n]*\n)"""\S)
