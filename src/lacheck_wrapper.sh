#!/bin/env bash
# shellcheck disable=SC2016
CYAN='\033[0;36m'
RESET='\033[0m'

# the pattern to match the error message (returns 3 groups)
PATTERN='^"(.*?)",\s*line\s*(\d+):\s*(.*?)$'
line='$1'
col='$2'
error='$3'

check_file() {
    path=$(dirname "$1")
    fname=$(basename "$1")
    cd "$path" || exit 1
    lacheck "$fname" | perl -ne "
      if (/$PATTERN/){
        if ($error !~ /Do not use @ in LaTeX macro names/) {
          print \"${CYAN}${path}/${line}:${col}:${RESET} ${error}\n\"
        }
      }"
}

exit_status=0

# Iterate over each file passed as an argument
for file in "$@"; do
    # NOTE: skip warning a la 'Style file `...' omitted.
    check_file "$file" | grep -v ".sty' omitted" && exit_status=1
done

exit $exit_status
