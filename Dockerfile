# Stage 1: Build Next.js static export
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim
WORKDIR /app

# Install uv
RUN pip install uv --no-cache-dir

# Install Python dependencies first (layer caching)
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --no-dev --frozen

# Copy backend source
COPY backend/ ./

# Copy frontend static export from Stage 1
COPY --from=frontend-builder /build/out ./static

# Create db directory (volume mount target)
RUN mkdir -p /app/db

# Point the DB to the volume-mounted directory
ENV FINALLY_DB_PATH=/app/db/finally.db

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
