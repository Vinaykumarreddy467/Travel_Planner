#!/usr/bin/env bash
#
# start.sh — Start the AI Travel Planner in production mode.
#
#   ./start.sh            # uses existing venv or .venv
#   ./start.sh --dev      # starts backend + frontend dev server with hot reload
#   ./start.sh --help     # show usage
#
set -euo pipefail

cd "$(dirname "$0")"

# ─── helpers ─────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[start]${NC} $*"; }
ok()    { echo -e "${GREEN}[start]${NC} $*"; }
warn()  { echo -e "${YELLOW}[start]${NC} $*"; }

# ─── detect venv ─────────────────────────────────────────
detect_venv() {
    if [ -d "venv" ]; then
        echo "venv"
    elif [ -d ".venv" ]; then
        echo ".venv"
    else
        echo ""
    fi
}

# ─── usage ───────────────────────────────────────────────
if [ "${1:-}" = "--help" ]; then
    echo "Usage: $0 [--dev]"
    echo ""
    echo "  (no flag)   Build frontend + serve everything on port 8000"
    echo "  --dev       Start backend (port 8000) + frontend dev server (port 5173)"
    echo "  --help      Show this help"
    exit 0
fi

# ─── validate .env ───────────────────────────────────────
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        warn ".env not found — copying .env.example to .env"
        cp .env.example .env
        warn "Edit .env with your API keys before starting"
    else
        warn ".env not found — API keys may be missing"
    fi
fi

# ─── activate venv ───────────────────────────────────────
VENV_DIR="$(detect_venv)"
if [ -z "$VENV_DIR" ]; then
    warn "No virtual environment found — creating one"
    python3 -m venv venv
    VENV_DIR="venv"
    source "$VENV_DIR/bin/activate"
    pip install -q -r requirements.txt
    ok "Virtual environment created and dependencies installed"
else
    source "$VENV_DIR/bin/activate"
    ok "Using virtual environment: $VENV_DIR"
fi

# ─── DEV MODE ────────────────────────────────────────────
if [ "${1:-}" = "--dev" ]; then
    info "Starting in DEV mode (two processes)..."

    # Ensure frontend dependencies
    if [ ! -d "frontend/node_modules" ]; then
        info "Installing frontend dependencies..."
        (cd frontend && npm install)
    fi

    # Kill leftover processes if any
    pkill -f "uvicorn backend.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    sleep 1

    # Start backend in background
    info "Starting backend on port 8000..."
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!

    # Start frontend dev server in background
    info "Starting frontend dev server on port 5173..."
    (cd frontend && npm run dev) &
    FRONTEND_PID=$!

    echo ""
    ok "==================================="
    ok "  Backend:  http://localhost:8000"
    ok "  Frontend: http://localhost:5173"
    ok "  PIDs:     backend=$BACKEND_PID  frontend=$FRONTEND_PID"
    ok "==================================="
    echo ""
    info "Run './stop.sh' to stop all processes"
    echo ""

    # Save PIDs so stop.sh can kill them
    echo "$BACKEND_PID" > .start-pids
    echo "$FRONTEND_PID" >> .start-pids

    # Wait for either process to exit
    wait
    exit 0
fi

# ─── PRODUCTION MODE (default) ───────────────────────────
info "Starting in PRODUCTION mode (single process)..."

# Build the frontend
if [ ! -d "frontend/node_modules" ]; then
    info "Installing frontend dependencies..."
    (cd frontend && npm install)
fi

info "Building frontend..."
(cd frontend && npm run build)
ok "Frontend built"

# Kill leftover process if any
pkill -f "uvicorn backend.main:app" 2>/dev/null || true
sleep 1

# Start the unified server
PORT="${PORT:-8000}"
info "Starting server on port $PORT..."
uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" &
SERVER_PID=$!

echo ""
ok "==================================="
ok "  App running at: http://localhost:$PORT"
ok "  PID:            $SERVER_PID"
ok "==================================="
echo ""
info "Run './stop.sh' to stop"

echo "$SERVER_PID" > .start-pids

wait
