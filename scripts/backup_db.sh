#!/bin/bash

# Configuration
BACKUP_DIR="/root/backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="significia_db_$TIMESTAMP.sql"
CONTAINER_NAME="significia-postgres-prod"
DB_USER="significia"
DB_NAME="significia"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Run pg_dump inside the container
echo "Starting database backup for $DB_NAME..."
docker exec $CONTAINER_NAME pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/$BACKUP_NAME

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup successful: $BACKUP_DIR/$BACKUP_NAME"
    
    # Compress the backup
    gzip $BACKUP_DIR/$BACKUP_NAME
    echo "Backup compressed: $BACKUP_DIR/$BACKUP_NAME.gz"
    
    # Remove backups older than 7 days
    find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +7 -delete
    echo "Old backups cleaned up."
else
    echo "Backup failed!"
    exit 1
fi
