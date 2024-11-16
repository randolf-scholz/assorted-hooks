# python-system-exit

Use `raise SystemExit` instead of `sys.exit()`.

## Rationale

In essence, `sys.exit` does nothing else than `raise SystemExit`. Using the latter is more explicit, and doesn't require importing the `sys` module.

- <https://github.com/python/cpython/blob/2313f8421080ceb3343c6f5d291279adea85e073/Python/sysmodule.c#L853>
- <https://mail.python.org/pipermail/python-list/2016-April/857869.html>
- <https://stackoverflow.com/questions/13992662/using-sys-exit-or-systemexit-when-to-use-which>
