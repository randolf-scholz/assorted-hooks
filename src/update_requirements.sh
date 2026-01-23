#!/usr/bin/env sh
# Wrapper script to run `src/update_requirements.py` with a suitable Python.
# Prefers the active virtual environment interpreter to keep dependency
# resolution consistent with the venv.

set -eu # `-e` exit on error, `-u` error on unset variables

# If a virtual environment is active and has an executable Python, use it.
if [ -n "${VIRTUAL_ENV-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
	PY="${VIRTUAL_ENV}/bin/python"
else
	echo "Error: no active virtual environment found (\`VIRTUAL_ENV\` is unset) or \`$VIRTUAL_ENV/bin/python\` is not executable." >&2
	echo "Activate a venv and re-run, e.g.: \`source .venv/bin/activate\`" >&2
	exit 1
fi

# Replace this shell process with the Python process.
exec "$PY" ./src/update_requirements.py "$@"
