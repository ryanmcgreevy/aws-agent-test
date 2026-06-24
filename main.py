"""
FastAPI HTTP server — AgentCore Runtime HTTP protocol contract.

AgentCore requires:
  - GET  /health  → { "status": "healthy" }
  - POST /invoke  → accepts JSON body, returns JSON response
  - Port 8080
  - Graceful SIGTERM handling
"""

import json
import logging
import os
import signal
import sys
from pathlib import Path

import boto3
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent import run

# AgentCore injects these environment variables at runtime
RUNTIME_ID = os.environ.get("RUNTIME_ID", "local")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Optional: Knowledge Base ID for RAG (set via build environment or CodeBuild)
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID")

# Remote endpoint configuration (for testing against deployed AgentCore runtime)
AGENT_RUNTIME_ARN = os.environ.get("AGENT_RUNTIME_ARN")
AGENT_RUNTIME_ID = os.environ.get("AGENT_RUNTIME_ID")
AGENT_ENDPOINT_NAME = os.environ.get("AGENT_ENDPOINT_NAME", "prod")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID")

# Determine if remote endpoint is configured
REMOTE_ENABLED = bool(AGENT_RUNTIME_ARN or (AGENT_RUNTIME_ID and AWS_ACCOUNT_ID))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Strands Agent", version="0.1.0")


# ── Request / Response models ────────────────────────────────────────────────

class InvokeRequest(BaseModel):
    """Accept both 'input' and 'prompt' keys for compatibility with invoke.sh and AgentCore playground."""
    input: str | None = None
    prompt: str | None = None
    session_id: str | None = None

    def get_text(self) -> str:
        """Extract the user input from either 'input' or 'prompt' field."""
        text = self.input or self.prompt
        if not text:
            raise ValueError("Either 'input' or 'prompt' must be provided")
        return text.strip()


class InvokeResponse(BaseModel):
    response: str
    session_id: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """AgentCore health check — must return 200 for the endpoint to be READY."""
    return {"status": "healthy", "runtime_id": RUNTIME_ID}


@app.get("/")
async def serve_ui():
    """Serve the test UI (ui.html). Available for local testing only."""
    ui_path = Path(__file__).resolve().parent / "ui.html"
    if not ui_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return FileResponse(ui_path, media_type="text/html")


@app.get("/remote-config")
async def get_remote_config():
    """Tell the UI whether remote endpoint testing is available."""
    return {
        "enabled": REMOTE_ENABLED,
        "endpoint_name": AGENT_ENDPOINT_NAME if REMOTE_ENABLED else None,
        "region": AWS_REGION if REMOTE_ENABLED else None,
    }


@app.post("/invoke-remote", response_model=InvokeResponse)
async def invoke_remote(body: InvokeRequest):
    """Invoke the remote AgentCore Runtime endpoint. Requires AGENT_RUNTIME_ARN or AGENT_RUNTIME_ID + AWS_ACCOUNT_ID."""
    if not REMOTE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Remote endpoint not configured. Set AGENT_RUNTIME_ARN or AGENT_RUNTIME_ID + AWS_ACCOUNT_ID.",
        )

    logger.info("Received remote invoke request for endpoint=%s", AGENT_ENDPOINT_NAME)

    try:
        user_input = body.get_text()
        if not user_input:
            raise ValueError("'input' or 'prompt' must be a non-empty string")

        # Build the payload for AgentCore
        payload = {"input": user_input}
        if body.session_id:
            payload["session_id"] = body.session_id

        # Use boto3 to invoke the remote endpoint
        agentcore_client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)

        invoke_kwargs = {
            "qualifier": AGENT_ENDPOINT_NAME,
            "payload": json.dumps(payload).encode("utf-8"),
            "contentType": "application/json",
            "accept": "application/json",
        }

        # Use ARN if available, otherwise build from ID + account
        if AGENT_RUNTIME_ARN:
            invoke_kwargs["agentRuntimeArn"] = AGENT_RUNTIME_ARN
        else:
            invoke_kwargs["agentRuntimeArn"] = (
                f"arn:aws:bedrock-agentcore:{AWS_REGION}:{AWS_ACCOUNT_ID}:runtime/{AGENT_RUNTIME_ID}"
            )

        response = agentcore_client.invoke_agent_runtime(**invoke_kwargs)

        # Parse the response body
        response_body = json.loads(response["payload"].read().decode("utf-8"))
        session_id = response_body.get("session_id", body.session_id or "")

        logger.info("Remote agent responded successfully")
        return InvokeResponse(response=response_body.get("response", ""), session_id=session_id)

    except ValueError as exc:
        logger.warning("Invalid request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Remote agent error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Remote agent invocation failed: {str(exc)}",
        ) from exc


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(body: InvokeRequest):
    """Main invocation endpoint. Calls the Strands agent and returns the result."""
    logger.info("Received invoke request (runtime_id=%s)", RUNTIME_ID)
    try:
        user_input = body.get_text()
        if not user_input:
            raise ValueError("'input' or 'prompt' must be a non-empty string")
        result, session_id = run(user_input, session_id=body.session_id)
        logger.info("Agent responded successfully")
        return InvokeResponse(response=result, session_id=session_id)
    except ValueError as exc:
        logger.warning("Invalid request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
