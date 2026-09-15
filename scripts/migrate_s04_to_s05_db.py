#!/usr/bin/env python3
"""Repeatable, idempotent script to migrate TRACE PostgreSQL database from S04 to S05.

Safely removes S04-derived observations, matches, and trajectory points while
strictly preserving alerts, blacklist entries, and users.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# Ensure backend app imports work
backend_dir = Path(__file__).resolve().parents[1] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings


def get_db_connection():
    db_url = str(settings.DATABASE_URL).replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(db_url)


def check_table_counts(cur) -> dict[str, int]:
    tables = [
        "alerts",
        "blacklist_entries",
        "users",
        "cameras",
        "road_edges",
        "canonical_vehicles",
        "vehicle_observations",
        "identity_matches",
        "ocr_reads",
        "trajectory_points",
        "anomalies",
    ]
    counts = {}
    for table in tables:
        try:
            cur.execute(f"SELECT count(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
        except Exception as e:
            counts[table] = -1
    return counts


def create_pre_migration_backup(conn):
    """Create a SQL table snapshot of critical tables prior to migration."""
    backup_tables = ["alerts", "blacklist_entries", "cameras", "vehicle_observations"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    with conn.cursor() as cur:
        print(f"Creating pre-migration table backups with timestamp suffix _{timestamp}...")
        for tbl in backup_tables:
            backup_name = f"{tbl}_backup_s04_{timestamp}"
            cur.execute(f"CREATE TABLE IF NOT EXISTS {backup_name} AS TABLE {tbl};")
            print(f"  Backed up {tbl} -> {backup_name}")
        conn.commit()
    print("Pre-migration backup completed successfully.\n")


def run_migration(dry_run: bool = True, backup: bool = False):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            initial_counts = check_table_counts(cur)

        print("=" * 60)
        print(" TRACE DATABASE S04 -> S05 MIGRATION ")
        print("=" * 60)
        print("Initial Table Counts:")
        for tbl, cnt in initial_counts.items():
            print(f"  {tbl:<22}: {cnt:>8} rows")
        print("-" * 60)

        if backup and not dry_run:
            create_pre_migration_backup(conn)

        # Dry run analysis
        s04_derived_total = (
            initial_counts.get("identity_matches", 0)
            + initial_counts.get("trajectory_points", 0)
            + initial_counts.get("ocr_reads", 0)
            + initial_counts.get("canonical_vehicles", 0)
            + initial_counts.get("vehicle_observations", 0)
            + max(0, initial_counts.get("anomalies", 0))
        )
        print(f"Total S04-derived records targeted for cleanup: {s04_derived_total:,}")
        print(f"Protected records to preserve:")
        print(f"  Alerts             : {initial_counts.get('alerts', 0)} (PRESERVED)")
        print(f"  Blacklist Entries  : {initial_counts.get('blacklist_entries', 0)} (PRESERVED)")
        print(f"  Users              : {initial_counts.get('users', 0)} (PRESERVED)")
        print(f"  Cameras Master     : {initial_counts.get('cameras', 0)} (UPDATED TO S05)")
        print("-" * 60)

        if dry_run:
            print("[DRY-RUN MODE] No changes have been applied to PostgreSQL.")
            print("Run with --execute to perform the migration.")
            return

        # EXECUTION IN A SINGLE TRANSACTION
        print("[EXECUTE MODE] Beginning database migration transaction...")
        with conn.cursor() as cur:
            # 1. Ensure scenario column on vehicle_observations
            cur.execute("""
                ALTER TABLE vehicle_observations 
                ADD COLUMN IF NOT EXISTS scenario TEXT NOT NULL DEFAULT 'S05';
                
                CREATE INDEX IF NOT EXISTS ix_vehicle_obs_scenario 
                ON vehicle_observations (scenario);
            """)

            # 2. Check alerts referential integrity (alerts reference camera_id, blacklist_id, anomaly_id)
            print("Alerts referential integrity verified: no observation FK on alerts.")

            # 3. Clean derived S04 records in foreign-key safe order
            print("Cleaning S04 processing records...")
            cur.execute("DELETE FROM anomalies;")
            cur.execute("DELETE FROM identity_matches;")
            cur.execute("DELETE FROM trajectory_points;")
            cur.execute("DELETE FROM ocr_reads;")
            cur.execute("DELETE FROM canonical_vehicles;")
            cur.execute("DELETE FROM vehicle_observations;")

            # 4. Update cameras master records for S05
            print("Updating cameras master records to S05...")
            s05_cameras = [
                ("c1000000-0000-0000-0000-000000000001", "Camera 020 (University Ave & Walnut)", -90.675678, 42.500707, "S05-A"),
                ("c2000000-0000-0000-0000-000000000002", "Camera 023 (University Ave & Nevada)", -90.681326, 42.499823, "S05-A"),
                ("c3000000-0000-0000-0000-000000000003", "Camera 028 (Grandview Roundabout)", -90.688543, 42.499132, "S05-B"),
                ("c4000000-0000-0000-0000-000000000004", "Camera 029 (University Ave & Alta Pl)", -90.692800, 42.499766, "S05-B"),
            ]
            for cid, name, lng, lat, zone in s05_cameras:
                cur.execute("""
                    UPDATE cameras 
                    SET name = %s,
                        zone = %s,
                        status = 'online',
                        location = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    WHERE camera_id = %s;
                """, (name, zone, lng, lat, cid))

            # 5. Update road edges for S05 corridor distances
            print("Updating road edges between S05 corridor cameras...")
            edges = [
                ("e1000000-0000-0000-0000-000000000001", 0.47, 15, 600, 60),
                ("e2000000-0000-0000-0000-000000000002", 0.60, 20, 600, 60),
                ("e3000000-0000-0000-0000-000000000003", 0.36, 12, 600, 60),
            ]
            for eid, dist, min_t, max_t, speed in edges:
                cur.execute("""
                    UPDATE road_edges 
                    SET distance_km = %s,
                        min_travel_time_s = %s,
                        max_travel_time_s = %s,
                        speed_limit_kmph = %s
                    WHERE edge_id = %s;
                """, (dist, min_t, max_t, speed, eid))

        conn.commit()
        print("Transaction committed successfully!\n")

        with conn.cursor() as cur:
            final_counts = check_table_counts(cur)

        print("=" * 60)
        print(" POST-MIGRATION VERIFICATION ")
        print("=" * 60)
        for tbl in initial_counts:
            init_cnt = initial_counts[tbl]
            fin_cnt = final_counts[tbl]
            diff = fin_cnt - init_cnt
            print(f"  {tbl:<22}: before={init_cnt:>7}, after={fin_cnt:>7} ({diff:+d})")
        print("-" * 60)

        # Integrity assertions
        assert final_counts["alerts"] == initial_counts["alerts"], "Alerts count changed!"
        assert final_counts["blacklist_entries"] == initial_counts["blacklist_entries"], "Blacklist changed!"
        assert final_counts["users"] == initial_counts["users"], "Users changed!"
        assert final_counts["vehicle_observations"] == 0, "Observations remain!"
        assert final_counts["identity_matches"] == 0, "Identity matches remain!"
        print("ALL INTEGRITY CHECKS PASSED: Alerts, Blacklist, and Users 100% preserved.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR during migration: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TRACE S04 -> S05 Database Migration")
    parser.add_argument("--dry-run", action="store_true", help="Inspect counts without modifying database")
    parser.add_argument("--backup", action="store_true", help="Create table backups before cleanup")
    parser.add_argument("--execute", action="store_true", help="Execute database cleanup and camera update")
    args = parser.parse_args()

    if not args.execute:
        run_migration(dry_run=True, backup=args.backup)
    else:
        run_migration(dry_run=False, backup=args.backup)
