"""Optional long-running worker: blpop Redis ingest jobs."""

from __future__ import annotations

import logging
import time

from app.core.db import SessionLocal, init_db
from app.services.ingest import process_document
from app.services.redis_queue import dequeue_ingest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest_worker")


def main() -> None:
    init_db()
    logger.info("ingest worker started")
    while True:
        job = dequeue_ingest(timeout=5)
        if not job:
            continue
        document_id = job.get("document_id")
        if not document_id:
            continue
        db = SessionLocal()
        try:
            process_document(db, document_id)
        finally:
            db.close()
        time.sleep(0.05)


if __name__ == "__main__":
    main()
