#!/usr/bin/env bash
# Uses a private libpq service/passfile and operator-provided AWS credentials.
set -euo pipefail
umask 077
: "${PGSERVICE:?Set the libpq service name}"
: "${BACKUP_DIRECTORY:?Set a private local backup directory}"
: "${BACKUP_S3_PREFIX:?Set s3://private-bucket/prefix}"
[[ "$BACKUP_S3_PREFIX" == s3://* ]] || { echo 'Invalid S3 backup prefix' >&2; exit 2; }
mkdir -p "$BACKUP_DIRECTORY"
chmod 700 "$BACKUP_DIRECTORY"
exec 9>"$BACKUP_DIRECTORY/.backup.lock"
flock -n 9 || exit 0
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_path="$BACKUP_DIRECTORY/pain-narratives-$stamp.dump"
partial_path="$backup_path.partial"
trap 'rm -f "$partial_path"' EXIT
pg_dump --format=custom --file="$partial_path"
# Structural validation only; run the documented isolated restore separately.
pg_restore --list "$partial_path" >/dev/null
mv "$partial_path" "$backup_path"
aws s3 cp "$backup_path" "${BACKUP_S3_PREFIX%/}/$(basename "$backup_path")" --sse AES256 --only-show-errors
# Delete only this script's old local dumps after a successful upload.
find "$BACKUP_DIRECTORY" -maxdepth 1 -type f -name 'pain-narratives-*.dump' -mtime +7 -delete
