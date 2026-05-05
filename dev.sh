#!/usr/bin/env bash
# =============================================================================
# Project Rain — Local Development Startup
# =============================================================================
# Usage: ./dev.sh
#
# Starts infrastructure containers (postgres, redis, qdrant, minio, code-server)
# via docker compose, then launches rain-api and workshop-web locally via bun.
# =============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()  { printf "${CYAN}[rain]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[  ok]${NC} %s\n" "$*"; }
warn() { printf "${YELLOW}[warn]${NC} %s\n" "$*"; }
err()  { printf "${RED}[ err]${NC} %s\n" "$*"; }

# ── Prerequisites ────────────────────────────────────────────────────────────

check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    err "$1 is required but not found. Please install it first."
    exit 1
  fi
  ok "$1 found: $($1 --version 2>&1 | head -n1)"
}

log "Checking prerequisites..."
check_cmd docker
check_cmd bun
check_cmd uv

# ── Infrastructure ───────────────────────────────────────────────────────────

log "Starting infrastructure services..."
docker compose -f docker-compose.dev.yml up -d --wait 2>&1 | while IFS= read -r line; do
  printf "${CYAN}[docker]${NC} %s\n" "$line"
done

# Verify critical services
for svc in postgres redis qdrant minio code-server; do
  if docker compose -f docker-compose.dev.yml ps --status running "$svc" 2>/dev/null | grep -q "$svc"; then
    ok "$svc is running"
  else
    warn "$svc may not be running — some features may be unavailable"
  fi
done

# ── Application ──────────────────────────────────────────────────────────────

log "Installing dependencies..."
bun install --frozen-lockfile 2>&1 | while IFS= read -r line; do
  printf "${CYAN}[bun]${NC} %s\n" "$line"
done

log ""
log "Starting Rain API (FastAPI + Uvicorn) on http://localhost:8000"
log "Starting Workshop Web (Next.js) on http://localhost:3000"
log "Code-Server available at http://localhost:8080"
log ""
log "Press Ctrl+C to stop all services"
log ""

# Trap Ctrl+C to clean up
cleanup() {
  log ""
  log "Shutting down..."
  docker compose -f docker-compose.dev.yml down 2>/dev/null || true
  ok "Infrastructure stopped."
  exit 0
}
trap cleanup SIGINT SIGTERM

# Run both apps via bun (foreground)
bun run dev &
BUN_PID=$!

wait "$BUN_PID"
cleanup
