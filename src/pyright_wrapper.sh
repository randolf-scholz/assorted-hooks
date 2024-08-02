#!/bin/env bash
BOLD_RED='\033[1;31m'
RESET='\033[0m'
PATTERN="(?<=$PWD/)(.*:.*)" # the pattern to match the error message
# We only keep the first line which holds the path to the file.

# NOTE: script -c preserves the colors of the output
result=$(script -c "pyright $*" /dev/null | grep --color=never -Po "$PATTERN");
# NOTE: wc -l gives incorrect count if no matches.
# REF: https://stackoverflow.com/a/42399738
count=$(echo -n "$result" | grep -c "^");

if [ "$count" -ne 0 ]; then
  echo "$result";
  echo "${BOLD_RED}Found ${count} errors${RESET}";
  exit 1;
fi
