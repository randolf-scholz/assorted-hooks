#!/usr/bin/env bash
repo=$(git rev-parse --show-toplevel)
cd "$repo" || exit 1
pre-commit try-repo "$repo" pyright-concise --verbose --all-files --hook-stage manual
cd "$repo" || exit 1
