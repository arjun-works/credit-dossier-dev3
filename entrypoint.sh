#!/bin/sh
set -e

# Track background child process PIDs for graceful shutdown
CHILD_PIDS=""

cleanup() {
    echo "[entrypoint] Received termination signal. Shutting down child processes..."
    for pid in $CHILD_PIDS; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    echo "[entrypoint] All child processes stopped."
}

trap cleanup INT TERM EXIT

# 1. Start Local MCP Server in background on 127.0.0.1:8001 (if present)
if [ -d "/app/mcp" ] && [ -f "/app/mcp/server.py" ]; then
    echo "[entrypoint] Starting Local MCP server on 127.0.0.1:8001..."
    (cd /app/mcp && python server.py) &
    MCP_PID=$!
    CHILD_PIDS="$CHILD_PIDS $MCP_PID"
fi

# 2. Start FastAPI Backend in background on 127.0.0.1:8000
echo "[entrypoint] Starting FastAPI backend on 127.0.0.1:8000..."
(cd /app/backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!
CHILD_PIDS="$CHILD_PIDS $BACKEND_PID"

# 3. Start Frontend production preview server in background on 127.0.0.1:3000
echo "[entrypoint] Starting Frontend preview server on 127.0.0.1:3000..."
(cd /app/frontend && npm run preview -- --port 3000 --host 127.0.0.1) &
FRONTEND_PID=$!
CHILD_PIDS="$CHILD_PIDS $FRONTEND_PID"

# 4. Execute Caddy in foreground as the root gateway listening on Railway PORT
echo "[entrypoint] Starting Caddy gateway on port ${PORT:-8080}..."
exec caddy run --config /app/Caddyfile --adapter caddyfile

