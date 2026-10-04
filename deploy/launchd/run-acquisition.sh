#!/bin/bash
# Mac launchd entry for scheduled acquisition-only runs (see docs/operations/SCHEDULED_ACQUISITION.md).
# Secrets and DATABASE_URL come from a private env file outside Git; nothing is passed in argv.
set -euo pipefail
CADENCE="${1:?usage: run-acquisition.sh daily|weekly|monthly}"
DEPLOY_DIR="${CIVIC_DEPLOY_DIR:-$HOME/Projects/civic-intel-deploy}"
ENV_FILE="${CIVIC_ACQUISITION_ENV_FILE:-$HOME/Developer/civic-intel-serve/acquisition.env}"
if [ ! -r "$ENV_FILE" ]; then
  echo "missing private env file: $ENV_FILE" >&2
  exit 78
fi
if [ "$(stat -f '%Lp' "$ENV_FILE")" != "600" ]; then
  echo "refusing $ENV_FILE: permissions must be 600" >&2
  exit 77
fi
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
cd "$DEPLOY_DIR"
exec "$DEPLOY_DIR/.venv/bin/python" -m workers.scheduled_acquisition --cadence "$CADENCE"
