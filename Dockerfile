# ==============================================================================
# Stage 1: Frontend Builder
# ==============================================================================
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

# Copy package manifests and install dependencies (do NOT use npm ci to prevent lockfile mismatch errors)
COPY frontend/package*.json ./
RUN npm install

# Copy source code and build production assets
COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Runtime Environment (FastAPI + MCP + Frontend Preview + Caddy)
# ==============================================================================
FROM python:3.11-slim

# Install system packages and Node.js 22 runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled static Caddy binary
COPY --from=caddy:2-alpine /usr/bin/caddy /usr/bin/caddy

WORKDIR /app

# Install backend and MCP Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
COPY mcp/requirements.txt /app/mcp/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/backend/requirements.txt \
    && pip install --no-cache-dir -r /app/mcp/requirements.txt

# Copy backend, MCP, and the built frontend directory
COPY backend/ /app/backend/
COPY mcp/ /app/mcp/
COPY --from=frontend-builder /app/frontend /app/frontend

# Copy Caddy gateway configuration and startup supervisor
COPY Caddyfile /app/Caddyfile
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Environment settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080

CMD ["/app/entrypoint.sh"]

