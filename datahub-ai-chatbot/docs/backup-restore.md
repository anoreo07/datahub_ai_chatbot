# Backup and Restore

This document describes backup and restore procedures for each data store.

## PostgreSQL

### Automated Backup (pg_dump)

```bash
# Daily backup
pg_dump -h localhost -p 5433 -U postgres -d chatbot \
  --format=custom --file=/backups/chatbot_$(date +%Y%m%d).dump

# Backup with compression
pg_dump -h localhost -p 5433 -U postgres -d chatbot \
  --format=custom --compress=9 --file=/backups/chatbot_daily.dump
```

### Automated Restore

```bash
# Restore from custom format backup
pg_restore -h localhost -p 5433 -U postgres -d chatbot \
  --clean --if-exists /backups/chatbot_20250101.dump

# Restore from plain SQL backup
psql -h localhost -p 5433 -U postgres -d chatbot < /backups/chatbot_20250101.sql
```

### Kubernetes

```bash
# Backup using pg_dump in pod
kubectl exec -n datahub-chatbot deploy/postgres -- \
  pg_dump -U postgres -d chatbot --format=custom > /tmp/backup.dump

# Restore
kubectl exec -n datahub-chatbot -i deploy/postgres -- \
  pg_restore -U postgres -d chatbot --clean < /tmp/backup.dump
```

### Retention Policy

| Environment | Frequency | Retention |
|-------------|-----------|-----------|
| Production  | Daily     | 30 days   |
| Staging     | Weekly    | 14 days   |
| Development | Manual    | N/A       |

## OpenSearch

OpenSearch serves as a search index that can be rebuilt from PostgreSQL data. However, taking snapshots is recommended for faster recovery.

### Snapshot Backup

```bash
# Register snapshot repository
curl -X PUT "http://localhost:9201/_snapshot/chatbot_backup" \
  -H "Content-Type: application/json" \
  -d '{"type": "fs", "settings": {"location": "/mount/backups"}}'

# Create snapshot
curl -X PUT "http://localhost:9201/_snapshot/chatbot_backup/snapshot_$(date +%Y%m%d)" \
  -H "Content-Type: application/json" \
  -d '{"indices": "datahub-rag-chunks-v1"}'

# List snapshots
curl "http://localhost:9201/_snapshot/chatbot_backup/_all"
```

### Snapshot Restore

```bash
# Restore from snapshot
curl -X POST "http://localhost:9201/_snapshot/chatbot_backup/snapshot_20250101/_restore" \
  -H "Content-Type: application/json" \
  -d '{"indices": "datahub-rag-chunks-v1"}'

# Check restore status
curl "http://localhost:9201/_snapshot/_restore/status"
```

### Rebuild from Database (Alternative)

If OpenSearch is corrupted, rebuild the index from PostgreSQL data:

```bash
python -m scripts.rebuild_index
```

### Retention Policy

| Environment | Frequency | Retention |
|-------------|-----------|-----------|
| Production  | Daily     | 14 days   |
| Others      | Manual    | N/A       |

## Document Storage

Document storage contains uploaded PDF, DOCX, and HTML files.

### Backup

```bash
# Local storage backup
tar -czf /backups/documents_$(date +%Y%m%d).tar.gz -C /data/documents .

# Kubernetes backup
kubectl cp datahub-chatbot/api-pod:/data/documents /backups/documents_$(date +%Y%m%d)
```

### Restore

```bash
# Local restore
tar -xzf /backups/documents_20250101.tar.gz -C /data/documents

# Kubernetes restore
kubectl cp /backups/documents_20250101 datahub-chatbot/api-pod:/data/documents
```

## Redis

Redis is used for caching, rate limiting, and ephemeral queues. It is **not a source of truth**.

- No formal backup required.
- On restart, Redis will be empty and repopulated from cache misses.

## Disaster Recovery

### Full Recovery Procedure

1. Bring up infrastructure services (PostgreSQL, Redis, OpenSearch)
2. Restore PostgreSQL from latest backup
3. Restore OpenSearch from snapshot OR run `python -m scripts.rebuild_index`
4. Restore document storage from backup
5. Start API and worker services
6. Verify health: `curl http://localhost:8000/ready`

### Recovery Time Objective (RTO)

| Tier    | Target   |
|---------|----------|
| Hot     | < 15 min |
| Warm    | < 1 hour |
| Cold    | < 4 hours|

### Recovery Point Objective (RPO)

| Tier    | Target       |
|---------|--------------|
| Hot     | < 5 minutes  |
| Warm    | < 24 hours   |
| Cold    | < 1 week     |

## Automation

For production, schedule backups via cron:

```bash
# PostgreSQL daily backup
0 1 * * * /usr/local/bin/backup-postgres.sh

# OpenSearch snapshot
0 2 * * * /usr/local/bin/backup-opensearch.sh

# Document storage
0 3 * * * /usr/local/bin/backup-documents.sh
```
