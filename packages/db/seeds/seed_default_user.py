"""Seed the default admin user.

Run once after migrations:
    python packages/db/seeds/seed_default_user.py

The admin password is taken from the env var RAIN_ADMIN_PASSWORD
(defaults to 'rain-admin-change-me' for local dev).
"""
import os
import sys
import pathlib

# Add packages/db/ to sys.path so 'schemas' is importable
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uuid import UUID
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from schemas import User

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_default_user() -> None:
    db_url = os.getenv("DATABASE_URL", "postgresql://rain:rain@localhost:5432/rain")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    admin_password = os.getenv("RAIN_ADMIN_PASSWORD", "rain-admin-change-me")

    with Session() as session:
        user = session.execute(
            select(User).where(User.id == DEFAULT_USER_ID)
        ).scalar_one_or_none()

        if user:
            # Ensure existing admin has a password hash (idempotent backfill)
            if not user.password_hash:
                user.password_hash = _pwd_ctx.hash(admin_password)
                user.role = "admin"
                user.is_active = True
                session.commit()
                print("Default admin password backfilled.")
            else:
                print("Default user already exists and has a password. Skipping.")
            return

        new_user = User(
            id=DEFAULT_USER_ID,
            username="fikri",
            email="fikri.mmstaqim@gmail.com",
            password_hash=_pwd_ctx.hash(admin_password),
            role="admin",
            is_active=True,
        )
        session.add(new_user)
        session.commit()
        print(f"Admin user 'fikri' seeded. Password: {admin_password}")
        print("CHANGE THIS PASSWORD via the Rain settings after first login.")


if __name__ == "__main__":
    seed_default_user()
