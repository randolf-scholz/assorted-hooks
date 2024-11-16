# pyarrow-timestamp-seconds

Flags `timestamp('s')` as a potential bug.

## Rationale

A time resolution of second does not round trip serialization.

See: <https://github.com/apache/arrow/issues/41382>