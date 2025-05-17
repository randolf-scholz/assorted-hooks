#!/usr/bin/env bash
repo=$(git rev-parse --show-toplevel)
pre-commit try-repo "$repo" check-signatures --verbose --all-files --hook-stage manual
