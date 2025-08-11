set -e
if [ -z "$1" ]; then
  echo "Usage: $0 path/to/backup.sql"; exit 1
fi
mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$1"
echo "Restored from $1"
