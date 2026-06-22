#!/usr/bin/env bash
#
# stop.sh — Stop the AI Travel Planner.
#
#   ./stop.sh            # stop all processes
#   ./stop.sh --hard     # force kill + clean up pid file
#
set -euo pipefail

cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[stop]${NC} $*"; }
ok()    { echo -e "${GREEN}[stop]${NC} $*"; }
warn()  { echo -e "${YELLOW}[stop]${NC} $*"; }

stopped_count=0

# ─── 1) Kill by PID file ─────────────────────────────────
if [ -f ".start-pids" ]; then
    while read -r pid; do
        if [ -n "$pid" ] && kill "$pid" 2>/dev/null; then
            info "Killed process $pid"
            stopped_count=$((stopped_count + 1))
        fi
    done < .start-pids
    rm -f .start-pids
fi

# ─── 2) Kill by process name (catch leftovers) ──────────
BACKEND_PIDS=$(pgrep -f "uvicorn backend.main:app" 2>/dev/null || true)
if [ -n "$BACKEND_PIDS" ]; then
    for pid in $BACKEND_PIDS; do
        kill "$pid" 2>/dev/null || true
        stopped_count=$((stopped_count + 1))
    done
    info "Killed uvicorn process(es): $BACKEND_PIDS"
fi

FRONTEND_PIDS=$(pgrep -f "vite" 2>/dev/null || true)
if [ -n "$FRONTEND_PIDS" ]; then
    for pid in $FRONTEND_PIDS; do
        kill "$pid" 2>/dev/null || true
        stopped_count=$((stopped_count + 1))
    done
    info "Killed vite process(es): $FRONTEND_PIDS"
fi

# ─── 3) Hard kill if --hard flag ─────────────────────────
if [ "${1:-}" = "--hard" ]; then
    if [ -n "$BACKEND_PIDS" ]; then
        kill -9 $BACKEND_PIDS 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PIDS" ]; then
        kill -9 $FRONTEND_PIDS 2>/dev/null || true
    fi
    rm -f .start-pids
    ok "Hard kill complete"
    exit 0
fi

# ─── done ────────────────────────────────────────────────
if [ "$stopped_count" -eq 0 ]; then
    warn "No running processes found"
else
    ok "Stopped $stopped_count process(es)"
fi
