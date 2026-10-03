#!/usr/bin/env bash
# Copy the canonical Mac PostgreSQL (SSOT) into the hosted read database used by a deployment.
# The hosted DB is a replaceable snapshot: it is backed up first, replaced from the source dump,
# then verified for identical schema revision and canonical counts. Credentials come only from
# the environment and are never written to files, logs or receipts.
set -euo pipefail

: "${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL is required (canonical Mac PostgreSQL)}"
: "${TARGET_DATABASE_URL:?TARGET_DATABASE_URL is required (hosted deployment PostgreSQL)}"
BACKUP_DIR="${BACKUP_DIR:?BACKUP_DIR is required (outside the repository)}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077
mkdir -p "$BACKUP_DIR"

COUNTS_SQL="select 'alembic', version_num from alembic_version
union all select 'people', count(*)::text from people
union all select 'organizations', count(*)::text from organizations
union all select 'claims', count(*)::text from claims
union all select 'claim_evidence', count(*)::text from claim_evidence
union all select 'sources', count(*)::text from sources
union all select 'source_snapshots', count(*)::text from source_snapshots
union all select 'feeder_observations', count(*)::text from feeder_observations
order by 1;"

counts() { psql "$1" -X -A -t -F' ' -v ON_ERROR_STOP=1 -c "$COUNTS_SQL"; }

echo "[1/5] source counts"
counts "$SOURCE_DATABASE_URL" | tee "$BACKUP_DIR/source-$STAMP.counts"

echo "[2/5] backup target"
pg_dump "$TARGET_DATABASE_URL" --format=custom --no-owner --file "$BACKUP_DIR/target-before-$STAMP.dump"
counts "$TARGET_DATABASE_URL" > "$BACKUP_DIR/target-before-$STAMP.counts" || true

echo "[3/5] dump source"
pg_dump "$SOURCE_DATABASE_URL" --format=custom --no-owner --file "$BACKUP_DIR/source-$STAMP.dump"

echo "[4/5] replace target from source dump"
pg_restore --dbname "$TARGET_DATABASE_URL" --clean --if-exists --no-owner --no-privileges \
  --single-transaction --exit-on-error "$BACKUP_DIR/source-$STAMP.dump"

echo "[5/5] verify target == source"
counts "$TARGET_DATABASE_URL" | tee "$BACKUP_DIR/target-after-$STAMP.counts"
if ! diff -u "$BACKUP_DIR/source-$STAMP.counts" "$BACKUP_DIR/target-after-$STAMP.counts"; then
  echo "VERIFY FAILED: restore from $BACKUP_DIR/target-before-$STAMP.dump" >&2
  exit 1
fi
echo "OK $STAMP source dump sha256 $(shasum -a 256 "$BACKUP_DIR/source-$STAMP.dump" | cut -d' ' -f1)"
