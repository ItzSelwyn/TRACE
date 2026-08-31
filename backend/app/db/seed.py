"""
Seed script for loading initial camera, road edge, and user data into the database.

Usage:
    cd backend
    python -m app.db.seed
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from geoalchemy2.elements import WKTElement
from passlib.context import CryptContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Base, Camera, CameraReliabilityProfile, RoadEdge, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SEED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed"


def seed():
    """Load seed data from JSON files into the database without duplicating rows."""
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    Base.metadata.create_all(engine)

    cameras_path = SEED_DIR / "cameras.json"
    road_edges_path = SEED_DIR / "road_edges.json"
    users_path = SEED_DIR / "users.json"

    with Session(engine) as session:
        if cameras_path.exists():
            with open(cameras_path, "r", encoding="utf-8") as fh:
                cameras_data = json.load(fh)

            inserted = 0
            for camera_data in cameras_data:
                camera_id = uuid.UUID(camera_data["camera_id"])
                if session.get(Camera, camera_id):
                    continue

                camera = Camera(
                    camera_id=camera_id,
                    name=camera_data["name"],
                    location=WKTElement(f'POINT({camera_data["longitude"]} {camera_data["latitude"]})', srid=4326),
                    zone=camera_data["zone"],
                    status=camera_data.get("status", "online"),
                )
                session.add(camera)
                session.flush()

                reliability = camera_data.get("reliability", {})
                profile = CameraReliabilityProfile(
                    camera_id=camera_id,
                    day_ocr_reliability=reliability.get("day_ocr_reliability", 0.90),
                    night_ocr_reliability=reliability.get("night_ocr_reliability", 0.75),
                    rain_ocr_reliability=reliability.get("rain_ocr_reliability", 0.65),
                    angle_ocr_reliability=reliability.get("angle_ocr_reliability", 0.85),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(profile)
                inserted += 1

            session.commit()
            print(f"Cameras seeded: {inserted} inserted.")

        if road_edges_path.exists():
            with open(road_edges_path, "r", encoding="utf-8") as fh:
                edges_data = json.load(fh)

            inserted = 0
            for edge_data in edges_data:
                edge_id = uuid.UUID(edge_data["edge_id"])
                if session.get(RoadEdge, edge_id):
                    continue

                edge = RoadEdge(
                    edge_id=edge_id,
                    from_camera_id=uuid.UUID(edge_data["from_camera_id"]),
                    to_camera_id=uuid.UUID(edge_data["to_camera_id"]),
                    distance_km=edge_data["distance_km"],
                    min_travel_time_s=edge_data["min_travel_time_s"],
                    max_travel_time_s=edge_data["max_travel_time_s"],
                    speed_limit_kmph=edge_data["speed_limit_kmph"],
                )
                session.add(edge)
                inserted += 1

            session.commit()
            print(f"Road edges seeded: {inserted} inserted.")

        if users_path.exists():
            with open(users_path, "r", encoding="utf-8") as fh:
                users_data = json.load(fh)

            inserted = 0
            for user_data in users_data:
                existing = session.execute(select(User).where(User.email == user_data["email"])).scalars().first()
                if existing:
                    continue

                user = User(
                    name=user_data["name"],
                    email=user_data["email"],
                    password_hash=pwd_context.hash(user_data["password"]),
                    role=user_data["role"],
                    created_at=datetime.now(timezone.utc),
                )
                session.add(user)
                inserted += 1

            session.commit()
            print(f"Users seeded: {inserted} inserted.")

    print("Seed complete.")


if __name__ == "__main__":
    seed()
