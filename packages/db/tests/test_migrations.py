import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def test_upgrade_downgrade_cycle():
    """
    Test the full migration lifecycle: base -> head -> base -> head.
    This ensures migrations are reversible and idempotent.
    """
    # Use the Postgres container from compose
    url = "postgresql://rain:rain@localhost:5432/rain"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)

    # 1. Upgrade to head
    command.upgrade(cfg, "head")

    # 2. Downgrade to base
    command.downgrade(cfg, "base")

    # 3. Upgrade to head again
    command.upgrade(cfg, "head")

    # Verify tables exist
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result]
        assert "users" in tables
        assert "conversations" in tables
        assert "messages" in tables

if __name__ == "__main__":
    # Run as script if pytest is not available in environment
    pytest.main([__file__])
