-- =============================================================================
-- create_tables.sql — BASE SCHEMA REFERENCE (stale — for documentation only)
-- =============================================================================
-- DO NOT run this directly to bootstrap a new database.
-- Use Alembic instead: `alembic upgrade head`
-- The first Alembic migration (3c737a5a064c) now creates base tables with
-- IF NOT EXISTS, so a completely fresh DB bootstraps correctly with:
--
--   cd db && alembic upgrade head && python -m db.seeds.seed_default_user
--
-- This file is kept as a human-readable reference for the base table shape
-- that existed before Alembic was introduced. It is NOT guaranteed to
-- reflect the current schema (use `alembic history` for that).
-- =============================================================================

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE users IS 'System users. Primary identity for data ownership.';
CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
COMMENT ON TABLE conversations IS 'User chat sessions. Soft-deleted via deleted_at.';
CREATE INDEX IF NOT EXISTS ix_conversations_user_id_created_at ON conversations (user_id, created_at);

-- Create message_role enum
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_role') THEN 
        CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system', 'tool');
    END IF;
END $$;

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role message_role NOT NULL,
    content TEXT NOT NULL,
    model VARCHAR(100),
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE messages IS 'Individual messages within a conversation.';
CREATE INDEX IF NOT EXISTS ix_messages_conversation_id_created_at ON messages (conversation_id, created_at);
