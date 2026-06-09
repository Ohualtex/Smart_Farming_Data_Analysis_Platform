# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copy application code
COPY . .

# Entrypoint'i çalıştırılabilir yap (prod'da `alembic upgrade head` → uvicorn)
RUN chmod +x /app/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Run the application (prod: migrate-then-serve; dev: create_all main.py'de)
CMD ["/app/docker-entrypoint.sh"]
