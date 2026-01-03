#!/usr/bin/env python
"""Retention cleanup job for expired attachments.

This script:
1. Finds attachments that have expired (expires_at <= now)
2. Marks them as DELETED in the database (soft delete)
3. Removes the physical files from MinIO/S3
4. Writes audit logs for compliance tracking

Run periodically via cron or scheduling system.
"""
import logging
import sys
from datetime import datetime, timedelta

import boto3

# Add app to path for imports
sys.path.insert(0, "/app")

from app.core.audit import write_audit
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.models import Attachment

LOG = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class RetentionCleanupJob:
    """Handles attachment retention and cleanup."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self.s3_client = self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3/MinIO client."""
        return boto3.client(
            "s3",
            endpoint_url=self.settings.S3_ENDPOINT,
            aws_access_key_id=self.settings.S3_ACCESS_KEY,
            aws_secret_access_key=self.settings.S3_SECRET_KEY,
            region_name=self.settings.S3_REGION,
        )

    def run_cleanup(self, dry_run: bool = False) -> dict:
        """Execute retention cleanup job.

        Args:
            dry_run: If True, only report what would be deleted without actually deleting

        Returns:
            Statistics dict with counts of processed attachments
        """
        session = SessionLocal()
        stats = {
            "expired_found": 0,
            "marked_deleted": 0,
            "removed_from_storage": 0,
            "failed": 0,
            "dry_run": dry_run,
        }

        try:
            # Find all expired attachments (ACTIVE status with expires_at in the past)
            now = datetime.utcnow()
            expired = (
                session.query(Attachment)
                .filter(
                    Attachment.status == "ACTIVE",
                    Attachment.expires_at.isnot(None),
                    Attachment.expires_at <= now,
                )
                .all()
            )

            stats["expired_found"] = len(expired)
            LOG.info(f"Found {len(expired)} expired attachments")

            for attachment in expired:
                try:
                    if not dry_run:
                        # Step 1: Mark as DELETED in database (soft delete)
                        attachment.status = "DELETED"
                        session.add(attachment)
                        session.commit()
                        stats["marked_deleted"] += 1

                        # Step 2: Remove from MinIO/S3
                        bucket = self.settings.MINIO_BUCKET or self.settings.S3_BUCKET
                        try:
                            self.s3_client.delete_object(
                                Bucket=bucket, Key=attachment.object_key
                            )
                            stats["removed_from_storage"] += 1
                            LOG.info(
                                f"Deleted attachment {attachment.id} "
                                f"(object_key: {attachment.object_key}) "
                                f"from storage"
                            )
                        except Exception as e:
                            LOG.error(
                                f"Failed to delete attachment {attachment.id} "
                                f"from storage: {e}"
                            )
                            stats["failed"] += 1
                            # Reset soft delete on failure
                            attachment.status = "ACTIVE"
                            session.add(attachment)
                            session.commit()
                            continue

                        # Step 3: Write audit log
                        try:
                            write_audit(
                                session,
                                actor_id=None,
                                action="ATTACHMENT_RETENTION_EXPIRED",
                                entity_type="attachment",
                                entity_id=attachment.id,
                                diff={
                                    "object_key": attachment.object_key,
                                    "ticket_id": attachment.ticket_id,
                                    "expires_at": (
                                        attachment.expires_at.isoformat()
                                        if attachment.expires_at
                                        else None
                                    ),
                                },
                            )
                        except Exception as e:
                            LOG.error(
                                f"Failed to write audit log for attachment {attachment.id}: {e}"
                            )

                    else:
                        # Dry run: just log what would happen
                        LOG.info(
                            f"[DRY RUN] Would delete attachment {attachment.id} "
                            f"(object_key: {attachment.object_key}, "
                            f"expires_at: {attachment.expires_at})"
                        )
                        stats["marked_deleted"] += 1

                except Exception as e:
                    LOG.error(f"Error processing attachment {attachment.id}: {e}")
                    stats["failed"] += 1
                    session.rollback()

        finally:
            session.close()

        LOG.info(
            f"Retention cleanup completed. "
            f"Expired: {stats['expired_found']}, "
            f"Marked deleted: {stats['marked_deleted']}, "
            f"Removed from storage: {stats['removed_from_storage']}, "
            f"Failed: {stats['failed']}"
        )

        return stats

    def set_retention_on_ticket_closure(
        self, ticket_id: int, retention_days: int = 30
    ) -> bool:
        """Set retention period when a ticket is closed.

        This calculates expiry date and sets expires_at for all attachments
        belonging to the closed ticket.

        Args:
            ticket_id: ID of closed ticket
            retention_days: How many days to retain attachments (default: 30)

        Returns:
            True if successful, False otherwise
        """
        session = SessionLocal()
        try:
            attachments = (
                session.query(Attachment)
                .filter(
                    Attachment.ticket_id == ticket_id, Attachment.status == "ACTIVE"
                )
                .all()
            )

            if not attachments:
                LOG.info(f"No active attachments found for ticket {ticket_id}")
                return True

            expires_at = datetime.utcnow() + timedelta(days=retention_days)

            for attachment in attachments:
                attachment.retention_days = retention_days
                attachment.expires_at = expires_at
                session.add(attachment)

            session.commit()
            LOG.info(
                f"Set retention period ({retention_days} days) "
                f"for {len(attachments)} attachments in ticket {ticket_id}"
            )
            return True

        except Exception as e:
            LOG.error(f"Failed to set retention for ticket {ticket_id}: {e}")
            session.rollback()
            return False
        finally:
            session.close()


def main():
    """Main entry point for the retention cleanup job."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Cleanup expired attachments based on retention policies"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual deletions)",
    )

    args = parser.parse_args()

    settings = get_settings()
    job = RetentionCleanupJob(settings)

    LOG.info("Starting retention cleanup job...")
    stats = job.run_cleanup(dry_run=args.dry_run)

    if args.dry_run:
        LOG.info("Dry-run mode - no changes were made")

    # Exit with non-zero code if there were failures
    if stats["failed"] > 0:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
