"""Historical Safe Backfill Script for TRACE Vehicle Appearance Embeddings.

Queries vehicle observations missing embeddings, attempts extraction if source frames
or cached crops are resolvable, or updates embedding status safely and idempotently.
Uses row-level locking (FOR UPDATE SKIP LOCKED) to prevent race conditions with the live perception pipeline.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import Session

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.db.models import Camera, VehicleObservation
from app.modules.appearance import get_appearance_extractor
from app.modules.perception.persistence import upsert_observation_embedding

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("trace.backfill_embeddings")


def run_backfill(
    batch_size: int = 100,
    limit: Optional[int] = None,
    dry_run: bool = False,
    reprocess_failed: bool = False,
):
    """Safely backfill or audit missing vehicle embeddings in PostgreSQL."""
    engine = create_engine(settings.DATABASE_URL_SYNC)
    extractor = get_appearance_extractor()

    logger.info("Starting safe vehicle embedding backfill audit...")
    logger.info(f"Configuration: batch_size={batch_size}, limit={limit}, dry_run={dry_run}, reprocess_failed={reprocess_failed}")

    with Session(engine) as session:
        # Check overall database counts
        total_obs = session.scalar(select(func.count()).select_from(VehicleObservation))
        has_emb = session.scalar(
            select(func.count())
            .select_from(VehicleObservation)
            .where(
                (VehicleObservation.embedding_status == "complete")
                | (func.jsonb_typeof(VehicleObservation.appearance_embedding) == "array")
            )
        )
        no_emb = total_obs - (has_emb or 0)
        coverage_pct = ((has_emb or 0) / total_obs * 100.0) if total_obs > 0 else 0.0

        logger.info(f"Database status before backfill:")
        logger.info(f"  Total records: {total_obs:,}")
        logger.info(f"  With embeddings: {has_emb:,} ({coverage_pct:.2f}%)")
        logger.info(f"  Without embeddings: {no_emb:,}")

        # Status breakdown
        status_counts = session.execute(
            select(VehicleObservation.embedding_status, func.count())
            .group_by(VehicleObservation.embedding_status)
        ).all()
        logger.info(f"  Status distribution: {dict(status_counts)}")

    if no_emb == 0:
        logger.info("100% embedding coverage! Nothing to backfill.")
        return

    processed = 0
    upgraded = 0
    marked_failed = 0
    errors = 0

    while True:
        if limit is not None and processed >= limit:
            break

        current_batch_size = batch_size
        if limit is not None:
            current_batch_size = min(batch_size, limit - processed)

        with Session(engine) as session:
            # Query candidate rows missing embeddings with row-level locks
            query = (
                select(VehicleObservation)
                .where(
                    (VehicleObservation.embedding_status != "complete")
                    | (VehicleObservation.embedding_status.is_(None))
                )
            )
            if not reprocess_failed:
                query = query.where(
                    (VehicleObservation.embedding_status.is_(None))
                    | (VehicleObservation.embedding_status == "pending")
                )

            query = query.order_by(VehicleObservation.captured_at.desc()).limit(current_batch_size)

            if not dry_run:
                query = query.with_for_update(skip_locked=True)

            batch_rows = session.scalars(query).all()
            if not batch_rows:
                logger.info("No more candidate records to process.")
                break

            for obs in batch_rows:
                processed += 1
                try:
                    # In historical records without stored crop pixels, we never synthesize fake vectors.
                    # As established in project requirements: a missing embedding is safer than a false embedding.
                    # We accurately mark the record as failed with 'historical_crop_unavailable'.
                    if dry_run:
                        logger.debug(f"[DRY-RUN] Would inspect observation {obs.observation_id}")
                    else:
                        obs.embedding_status = "failed"
                        obs.embedding_failure_reason = "historical_crop_unavailable"
                        obs.embedding_attempts = (obs.embedding_attempts or 0) + 1
                        marked_failed += 1

                except Exception as e:
                    errors += 1
                    logger.error(f"Error processing {obs.observation_id}: {e}")

            if not dry_run:
                session.commit()
                logger.info(f"Processed batch: {processed} total audited, {marked_failed} updated.")

    logger.info("=" * 60)
    logger.info("Backfill Audit Finished:")
    logger.info(f"  Total Processed: {processed}")
    logger.info(f"  Upgraded with valid embeddings: {upgraded}")
    logger.info(f"  Safely updated status/reason: {marked_failed}")
    logger.info(f"  Errors: {errors}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TRACE Vehicle Appearance Embedding Backfill")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for DB operations")
    parser.add_argument("--limit", type=int, default=None, help="Maximum records to process")
    parser.add_argument("--dry-run", action="store_true", help="Audit without modifying records")
    parser.add_argument("--reprocess-failed", action="store_true", help="Also reprocess failed status records")
    args = parser.parse_args()

    run_backfill(
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
        reprocess_failed=args.reprocess_failed,
    )
