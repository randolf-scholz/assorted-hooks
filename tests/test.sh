#!/usr/bin/env bash
repo=$(git rev-parse --show-toplevel)
cd "$repo" || exit 1
pre-commit try-repo "$repo" --verbose --all-files
cd "$repo" || exit 1
