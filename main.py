"""
FastAPI HTTP server — AgentCore Runtime HTTP protocol contract.

AgentCore requires:
  - GET  /health  → { "status": "healthy" }
  - POST /invoke  → accepts JSON body, returns JSON response
  - Port 8080
  - Graceful SIGTERM handling
"""

import logging
import os
import signal
import sys

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import run

# AgentCore injects these environment variables at runtime
RUNTIME_ID = os.environ.get("RUNTIME_ID", "local")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Strands Agent", version="0.1.0")


# ── Request / Response models ────────────────────────────────────────────────

class InvokeRequest(BaseModel):
    input: str


class InvokeResponse(BaseModel):
    response: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """AgentCore health check — must return 200 for the endpoint to be READY."""
    return {"status": "healthy", "runtime_id": RUNTIME_ID}


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(body: InvokeRequest):
    """Main invocation endpoint. Calls the Strands agent and returns the result."""
    logger.info("Received invoke request (runtime_id=%s)", RUNTIME_ID)
    if not body.input or not body.input.strip():
        raise HTTPException(status_code=400, detail="'input' must be a non-empty string")
    try:
        result = run(body.input)
        logger.info("Agent responded successfully")
        return InvokeResponse(response=result)
    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Agent invocation failed") from exc


# AgentCore integrations can invoke different HTTP paths depending on protocol
# adapters. Keep aliases to avoid path mismatch 404s.
@app.post("/invocations", response_model=InvokeResponse)
async def invoke_alias_invocations(body: InvokeRequest):
    return await invoke(body)


@app.post("/", response_model=InvokeResponse)
async def invoke_alias_root(body: InvokeRequest):
    return await invoke(body)


# ── Graceful shutdown ────────────────────────────────────────────────────────

def _shutdown(sig, frame):  # noqa: ARG001
    logger.info("Received SIGTERM — shutting down gracefully")
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown)


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info("Starting server on port %d (region=%s)", port, AWS_REGION)
    uvicorn.run(app, host="0.0.0.0", port=port)
