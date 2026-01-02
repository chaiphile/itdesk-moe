# Quick Reference - Retention & Redaction System

## API Usage

### Export Ticket with Redaction
```bash
# Export a ticket (applies redaction based on user permissions)
curl -X POST http://localhost:8000/api/v1/tickets/123/export \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"

# Response includes:
{
  "ticket_data": { /* ticket info - may be redacted */ },
  "messages": [ /* ticket messages */ ],
  "attachments": [
    {
      "id": 1,
      "original_filename": "***.pdf",  # Masked for CONFIDENTIAL
      "sensitivity_level": "CONFIDENTIAL",
      "size": null,  # Hidden for CONFIDENTIAL
      "status": "ACTIVE"
    }
  ]
}
```

## Configuration

### Environment Variables
```bash
# Default retention period (days)
ATTACHMENT_RETENTION_DAYS=30

# Cleanup job interval (seconds, default = 24 hours)
RETENTION_CLEANUP_INTERVAL=86400

# S3/MinIO settings (for physical deletion)
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

## Database Schema

### Attachment Columns
```sql
-- Sensitivity level: REGULAR, CONFIDENTIAL, RESTRICTED
sensitivity_level VARCHAR NOT NULL DEFAULT 'REGULAR'
CHECK(sensitivity_level IN ('REGULAR', 'CONFIDENTIAL', 'RESTRICTED'))

-- Days to retain after ticket closure
retention_days INTEGER

-- Soft delete marker: ACTIVE or DELETED
status VARCHAR NOT NULL DEFAULT 'ACTIVE'
CHECK(status IN ('ACTIVE', 'DELETED'))

-- When metadata was redacted
redacted_at TIMESTAMP WITH TIMEZONE

-- When attachment expires (for automatic cleanup)
expires_at TIMESTAMP WITH TIMEZONE
CREATE INDEX idx_attachment_expires_at ON attachments(expires_at)
```

## Permissions Required

### For Regular Export
```
CONFIDENTIAL_VIEW - To see CONFIDENTIAL attachment names
```

### For Full Export (RESTRICTED attachments)
```
EXPORT_CONFIDENTIAL - To export RESTRICTED attachments with full metadata
```

### Redaction Rules by Permission
| Attachment Level | No Permission | CONFIDENTIAL_VIEW | EXPORT_CONFIDENTIAL |
|------------------|--------------|-------------------|---------------------|
| REGULAR | ✅ Full | ✅ Full | ✅ Full |
| CONFIDENTIAL | ❌ Blocked (404) | ✅ Masked | ✅ Full |
| RESTRICTED | ❌ Blocked (404) | ❌ Blocked (404) | ✅ Full |

## Testing

### Run All Retention Tests
```bash
cd backend
pytest tests/test_retention_redaction_export.py tests/test_retention_cleanup.py -v
```

### Test Specific Feature
```bash
# Redaction rules
pytest tests/test_retention_redaction_export.py::TestRedactionRules -v

# Export basic auth
pytest tests/test_retention_redaction_export.py::TestExportBasic -v

# Retention cleanup logic
pytest tests/test_retention_cleanup.py -v
```

## Audit Logs

### Tracked Actions
- `TICKET_EXPORTED`: User exported ticket (success/denied)
- `ATTACHMENT_RETENTION_EXPIRED`: Attachment deleted after retention period

### Query Audit Logs
```python
from app.db.models import AuditLog

# Find all ticket exports
exports = db.query(AuditLog).filter(
    AuditLog.action == "TICKET_EXPORTED"
).all()

# Find retention cleanup events
cleanups = db.query(AuditLog).filter(
    AuditLog.action == "ATTACHMENT_RETENTION_EXPIRED"
).all()
```

## Docker Deployment

### Start Services
```bash
docker compose up -d postgres minio postgres-migrate retention-cleanup
```

### Verify Retention Service
```bash
# Check service is running
docker ps | grep retention-cleanup

# View logs
docker logs retention-cleanup

# Run cleanup manually (for testing)
docker exec retention-cleanup python scripts/retention_cleanup.py
```

## Retention Cleanup Job

### Manual Execution
```bash
cd backend
python scripts/retention_cleanup.py  # Normal run
python scripts/retention_cleanup.py --dry-run  # Preview only
```

### Programmatic Usage
```python
from app.scripts.retention_cleanup import RetentionCleanupJob
from app.db.session import SessionLocal

job = RetentionCleanupJob()
stats = job.run_cleanup(dry_run=False)

print(f"Expired: {stats['expired_found']}")
print(f"Deleted: {stats['marked_deleted']}")
print(f"Removed: {stats['removed_from_storage']}")
print(f"Failed: {stats['failed']}")
```

## Common Tasks

### Set Retention on Ticket Closure
```python
from app.scripts.retention_cleanup import RetentionCleanupJob

job = RetentionCleanupJob()
job.set_retention_on_ticket_closure(ticket_id=123, retention_days=30)
```

### Query Expired Attachments
```python
from datetime import datetime
from app.models import Attachment

now = datetime.utcnow()
expired = db.query(Attachment).filter(
    Attachment.status == "ACTIVE",
    Attachment.expires_at.isnot(None),
    Attachment.expires_at <= now
).all()
```

### Redact Ticket Data
```python
from app.core.redaction import RedactionEngine

engine = RedactionEngine.create_default()
redacted = engine.redact_ticket_export(
    ticket_data={...},
    has_export_permission=False
)
```

## Troubleshooting

### S3 Deletion Failures
- Check MinIO/S3 connectivity
- Verify credentials in environment
- Check S3 bucket permissions
- Review logs: `docker logs retention-cleanup`

### Retention Cleanup Not Running
- Verify service is running: `docker ps | grep retention-cleanup`
- Check logs: `docker logs retention-cleanup`
- Verify DATABASE_URL in docker-compose
- Ensure postgres is healthy

### Export Returning 404
- **Issue**: Ticket has CONFIDENTIAL attachments, user lacks CONFIDENTIAL_VIEW
- **Fix**: Grant user CONFIDENTIAL_VIEW permission in their role

- **Issue**: Ticket has RESTRICTED attachments, user lacks EXPORT_CONFIDENTIAL  
- **Fix**: Grant user EXPORT_CONFIDENTIAL permission in their role

### Export Returning 403
- **Issue**: User not in ticket's org scope
- **Fix**: Verify user org_unit_id matches ticket owner_org_unit_id (for org-scoped users)

## Performance Notes

- ✅ Expires_at column indexed for fast cleanup queries
- ✅ Soft delete (status='DELETED') avoids long DELETE operations
- ✅ S3 deletion happens asynchronously in cleanup job
- ✅ Redaction engine uses in-memory rules (no DB lookups)

## Security Notes

- ✅ All exports logged to audit trail
- ✅ Permission checks enforced server-side (not client-side)
- ✅ Redaction applied before data leaves API
- ✅ Org scope prevents cross-org access
- ✅ Soft delete preserves data for compliance/recovery

---

**For detailed documentation, see [RETENTION_IMPLEMENTATION_COMPLETE.md](RETENTION_IMPLEMENTATION_COMPLETE.md)**
