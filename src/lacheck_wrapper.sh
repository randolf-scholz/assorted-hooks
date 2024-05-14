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

# Iterate over each file passed as an argument
for file in "$@"; do check_file "$file" & done
