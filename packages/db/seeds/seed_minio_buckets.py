"""Seed MinIO buckets for Project Rain.

Creates the rain-uploads and rain-skill-artifacts buckets if they don't exist.
Idempotent: safe to run multiple times.

Usage:
    python -m db.seeds.seed_minio_buckets
"""
import os
from minio import Minio


def seed_minio_buckets(
    endpoint: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
) -> list[str]:
    """Create required MinIO buckets. Returns list of bucket names created or already existing."""
    endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "rain")
    secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "rainminio")

    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)

    required_buckets = ["rain-uploads", "rain-skill-artifacts"]
    created = []

    for bucket in required_buckets:
        if client.bucket_exists(bucket):
            print(f"Bucket '{bucket}' already exists. Skipping.")
        else:
            client.make_bucket(bucket)
            print(f"Bucket '{bucket}' created.")
        created.append(bucket)

    return created


if __name__ == "__main__":
    seed_minio_buckets()