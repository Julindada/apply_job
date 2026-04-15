# ---------- build stage ----------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install .

# ---------- runtime stage ----------
FROM python:3.13-slim

WORKDIR /app

# Copy the virtualenv from builder
COPY --from=builder /app/.venv /app/.venv

# Add venv to PATH so `apply-job` is on the PATH
ENV PATH="/app/.venv/bin:$PATH" \
    DATA_DIR=/app/data \
    PYTHONUNBUFFERED=1

# Copy application code (separate layer — changes here don't invalidate deps)
COPY src/ /app/src/

# Create data directory for checkpoints.db + CSV output
RUN mkdir -p /app/data

ENTRYPOINT ["apply-job"]
CMD ["--help"]
