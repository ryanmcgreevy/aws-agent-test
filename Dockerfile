# ── Stage 1: Install dependencies ───────────────────────────────────────────
# AgentCore runs on Graviton (ARM64). x86 images will NOT start.
FROM python:3.12-slim AS builder

WORKDIR /app
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


# ── Stage 2: Minimal runtime image ──────────────────────────────────────────
FROM python:3.12-slim

# Run as non-root for least-privilege
RUN useradd -r -u 1001 appuser

WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

# AgentCore default port
EXPOSE 8080

# Binds to 0.0.0.0 for AgentCore internal routing.
# Do NOT expose this container directly to the internet.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
