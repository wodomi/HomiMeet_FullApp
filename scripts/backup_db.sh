set -e
TIMESTAMP=$(date +%Y%m%d_%H%M)
BACKUP_DIR=${BACKUP_DIR:-./backups}
mkdir -p "$BACKUP_DIR"
mysqldump -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" > "$BACKUP_DIR/homimeet_${TIMESTAMP}.sql"
echo "Backup saved to $BACKUP_DIR/homimeet_${TIMESTAMP}.sql"
