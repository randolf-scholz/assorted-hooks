#!/usr/bin/env sh
# Wrapper script to run `src/check_clean_interface.py` with a suitable Python.
# Prefers the active virtual environment interpreter to keep dependency
# resolution consistent with the venv.

set -eu # `-e` exit on error, `-u` error on unset variables

# If a virtual environment is active and has an executable Python, use it.
if [ -n "${VIRTUAL_ENV-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
	PY="${VIRTUAL_ENV}/bin/python"
else
	PY="$(command -v python3 || command -v python)"
fi

# Replace this shell process with the Python process.
exec "$PY" ./src/check_clean_interface.py "$@"
