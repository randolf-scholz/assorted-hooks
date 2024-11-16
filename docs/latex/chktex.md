
# chktex

**Default configuration:** All checks are enabled except for

- `1`: *Command terminated with space.* (wrong advice[^warn1])
- `3`: *Enclose previous parentheses with `{}`.* (wrong advice[^warn3])
- `9`: *‘%s’ expected, found ‘%s’.* (interferes with half-open intervals[^warn9])
- `17`: *Number of ‘character’ doesn’t match the number of ‘character’.* (interferes with half-open intervals[^warn17])
- `19`: *You should use "`’`" (ASCII 39) instead of "`’`" (ASCII 180).* (gets confused by unicode[^warn19])
- `21`: *This command might not be intended.* (too many false positives[^warn21])
- `22`: *Comment displayed.* (not useful in the context of `pre-commit`)
- `30`: *Multiple spaces detected in output.*  (not useful when using spaces for indentation)
- `46`: *Use `\(...\)` instead of `$...$`.* (wrong advice[^warn21])

To manually select which checks to enable, add `args`-section to the hook configuration in `.pre-commit-config.yaml`.

**Usage Recommendations:**

- `30`: Consider enabling when using tabs for indentation.
- `41`: Keep enabled, but put `% chktex-file 41` inside `.sty` and `.cls` files.
- `44`: For block-matrices, the `nicematrix` package is recommended. Otherwise, it is suggested to allow individual tables by adding a `% chktex 44` comment after `\begin{tabular}{...}`.

[//]: # (footnotes)
[^warn1]: <https://tex.stackexchange.com/q/552210>
[^warn3]: <https://tex.stackexchange.com/q/529937>
[^warn9]: <https://tex.stackexchange.com/q/405583>
[^warn17]: <https://tex.stackexchange.com/q/405583>
[^warn19]: <https://github.com/nscaife/linter-chktex/issues/30>
[^warn21]: <https://tex.stackexchange.com/q/473080>
