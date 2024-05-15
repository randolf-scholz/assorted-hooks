#!/bin/env bash
# shellcheck disable=SC2016
BLUE='\033[0;34m'
PATTERN='^"(.*?)",\s*line\s*(\d+):\s*(.*?)$'
OUTPUT='/$1:$2:\033[0m $3\n'

check_file() {
    fdir=$(dirname "$1")
    fname=$(basename "$1")
    cd "$fdir" || exit 1
    lacheck "$fname" | perl -ne "if (m/$PATTERN/) {print \"${BLUE}${fdir}${OUTPUT}\"}"
}

exit_status=0

# Iterate over each file passed as an argument
for file in "$@"; do
    # NOTE: skip warning a la 'Style file `...' omitted.
    check_file "$file" | grep -v ".sty' omitted" && exit_status=1
done

exit $exit_status
