# python-double-comment

Checks for the presence of double comments in Python code,
matching the regex pattern `\#\s+\#`.

## Rationale

Such double comments can indicate commented-out code and are generally redundant.
Note that non-seperated hashtags like in `## heading`, which are used in Markdown,
are not affected by this rule.
