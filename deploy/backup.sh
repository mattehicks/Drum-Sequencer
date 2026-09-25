#!/usr/bin/env bash
# Consistent SQLite snapshot of the app database, kept 14 days locally,
# optionally copied to S3 (set S3_BUCKET, requires aws cli on the host).
# Cron (as the deploy user):  15 3 * * * /opt/d20/deploy/backup.sh >> /var/log/d20-backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT_DIR="${BACKUP_DIR:-$HOME/d20-backups}"
mkdir -p "$OUT_DIR"

docker compose exec -T app node --disable-warning=ExperimentalWarning -e "
  const { DatabaseSync } = require('node:sqlite');
  const db = new DatabaseSync(process.env.DB_FILE);
  db.exec(\"VACUUM INTO '/data/snapshot.db'\");
"
CID=$(docker compose ps -q app)
docker cp "$CID:/data/snapshot.db" "$OUT_DIR/d20-$STAMP.db"
docker compose exec -T app rm -f /data/snapshot.db
gzip -f "$OUT_DIR/d20-$STAMP.db"
echo "backup: $OUT_DIR/d20-$STAMP.db.gz"

if [[ -n "${S3_BUCKET:-}" ]]; then
  aws s3 cp "$OUT_DIR/d20-$STAMP.db.gz" "s3://$S3_BUCKET/d20/" --only-show-errors
  echo "uploaded to s3://$S3_BUCKET/d20/"
fi

find "$OUT_DIR" -name 'd20-*.db.gz' -mtime +14 -delete
