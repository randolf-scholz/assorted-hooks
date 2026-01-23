#!/usr/bin/env sh
set -eu

if [ -n "${VIRTUAL_ENV-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
  PY="${VIRTUAL_ENV}/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

exec "$PY" ./src/update_requirements.py "$@"
