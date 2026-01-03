"""Simple attachment scanner daemon that polls DB for PENDING attachments,
downloads objects from S3/MinIO and scans them using ClamAV (clamd INSTREAM).

This script is intentionally small and dependency-light so it can run as a
separate service in docker-compose. Unit tests mock network/storage so no
real ClamAV is required for tests.
"""

import logging
import os
import socket
import struct
import time
from datetime import datetime

import boto3
from app.core.audit import write_audit
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.models import Attachment

LOG = logging.getLogger("attachment_scanner")


def perform_clamav_instream_scan(
    data_bytes: bytes, host: str, port: int, timeout: int = 10
) -> str:
    """Send data to clamd INSTREAM and return one of: 'CLEAN','INFECTED','FAILED'."""
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as s:
            # start INSTREAM
            s.sendall(b"nINSTREAM\n")
            offset = 0
            chunk_size = 1024 * 64
            while offset < len(data_bytes):
                chunk = data_bytes[offset : offset + chunk_size]
                s.sendall(struct.pack(">I", len(chunk)))
                s.sendall(chunk)
                offset += len(chunk)
            # send zero-length to mark EOF
            s.sendall(struct.pack(">I", 0))
            # read response
            resp = b""
            while True:
                part = s.recv(4096)
                if not part:
                    break
                resp += part
                if b"\n" in resp:
                    break
            text = resp.decode(errors="ignore").strip()
            # Response like: stream: OK or stream: <name> FOUND
            if "OK" in text:
                return "CLEAN"
            if "FOUND" in text:
                return "INFECTED"
            LOG.warning("Unexpected clamd response: %s", text)
            return "FAILED"
    except Exception:
        LOG.exception("ClamAV scan failed")
        return "FAILED"


def scan_pending_once(settings):
    session = SessionLocal()
    s3 = boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )
    try:
        q = (
            session.query(Attachment)
            .filter(Attachment.scanned_status == "PENDING")
            .limit(20)
        )
        rows = q.all()
        if not rows:
            return 0

        for att in rows:
            try:
                LOG.info("Scanning attachment id=%s key=%s", att.id, att.object_key)
                # download object
                resp = s3.get_object(
                    Bucket=(settings.MINIO_BUCKET or settings.S3_BUCKET),
                    Key=att.object_key,
                )
                body = resp["Body"].read()

                # respect optional max bytes
                maxb = getattr(settings, "ATTACHMENT_SCAN_MAX_BYTES", None)
                if maxb:
                    body = body[: int(maxb)]

                result = perform_clamav_instream_scan(
                    body,
                    host=getattr(settings, "CLAMAV_HOST", "clamav"),
                    port=getattr(settings, "CLAMAV_PORT", 3310),
                )

                att.scanned_status = result
                att.scanned_at = datetime.utcnow()
                session.add(att)
                session.commit()

                write_audit(
                    session,
                    actor_id=None,
                    action="ATTACHMENT_SCANNED",
                    entity_type="attachment",
                    entity_id=att.id,
                    diff={
                        "result": result,
                        "object_key": att.object_key,
                        "ticket_id": att.ticket_id,
                    },
                )
            except Exception:
                session.rollback()
                try:
                    att.scanned_status = "FAILED"
                    att.scanned_at = datetime.utcnow()
                    session.add(att)
                    session.commit()
                except Exception:
                    session.rollback()
                try:
                    write_audit(
                        session,
                        actor_id=None,
                        action="ATTACHMENT_SCANNED",
                        entity_type="attachment",
                        entity_id=getattr(att, "id", None),
                        diff={
                            "result": "FAILED",
                            "object_key": getattr(att, "object_key", None),
                            "ticket_id": getattr(att, "ticket_id", None),
                        },
                    )
                except Exception:
                    LOG.exception("Failed to write failure audit")
        return len(rows)
    finally:
        session.close()


def main():
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    poll = int(
        os.environ.get(
            "ATTACHMENT_SCAN_POLL_SECONDS",
            getattr(settings, "ATTACHMENT_SCAN_POLL_SECONDS", 5),
        )
    )
    LOG.info(
        "Starting attachment scanner (clamav=%s:%s) poll=%s",
        getattr(settings, "CLAMAV_HOST", "clamav"),
        getattr(settings, "CLAMAV_PORT", 3310),
        poll,
    )
    while True:
        try:
            n = scan_pending_once(settings)
            if n:
                LOG.info("Scanned %d attachments", n)
        except Exception:
            LOG.exception("Scanner loop error")
        time.sleep(poll)


if __name__ == "__main__":
    main()
