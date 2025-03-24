# check-separator-length

Tests that "horizontal rule" comments terminate at column 88.

```python
# region implementation -------------------- <-- should terminate at column 88
```

## NOTE

This regex checks comments begin with a `#`, `%`, `//` (padded to length 2)
The first group is 0-82 or 84-unlimited characters
The construction `([-=—─═])\2{2}` checks for a separator character repeated 3 times
If the first group matches ≥84 characters, then the line is overlong (2+84+3=89 characters)
If it matches ≤82 characters, then the line is too short, given that it is detected as a separator.
(2 + 83 characters + separator + separator + separator = 88 characters)

The second group is a separator character, we consider the characters:

- `-` (U+002D: Hyphen-Minus)
- `=` (U+003D: Equals Sign)
- `—` (U+2014: Em Dash)
- `═` (U+2550: Box Drawings Double Horizontal)
- `─` (U+2500: Box Drawings Light Horizontal)
