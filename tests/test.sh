#!/usr/bin/env bash
repo=$(git rev-parse --show-toplevel)
pre-commit try-repo "$repo" --verbose --all-files
