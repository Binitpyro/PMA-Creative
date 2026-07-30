"""Zeni Standalone Server (FastAPI + Uvicorn) on port 8765."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import uvicorn

from src.server.ws_router import ZeniWSRouter, verify_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zeni.main")

app = FastAPI(title="Zeni Creative Module", version="0.1.0")
ws_router = ZeniWSRouter()


class SignupRequest(BaseModel):
    name: str
    email: str
    organization: str = ""
    use_case: str = ""


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Zeni Standalone"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.headers.get("x-local-access-token") or websocket.query_params.get("token")
    if not verify_access_token(token):
        logger.warning("Rejected unauthenticated WebSocket connection attempt.")
        await websocket.close(code=4008, reason="Unauthorized: Invalid or missing x-local-access-token")
        return

    await websocket.accept()
    logger.info("WebSocket client connected successfully.")

    try:
        while True:
            raw_msg = await websocket.receive_text()
            response_json = await ws_router.handle_message(raw_msg, token=token)
            await websocket.send_text(response_json)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


@app.post("/api/signup")
async def signup(req: SignupRequest):
    """Trial signup endpoint with automated triage decision log."""
    try:
        from src.business.triage import triage_trial_signup
        return triage_trial_signup(req.model_dump())
    except Exception as e:
        logger.error(f"Signup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def start():
    port = int(os.environ.get("ZENI_PORT", "8765"))
    host = os.environ.get("ZENI_HOST", "0.0.0.0")
    logger.info(f"Starting Zeni standalone server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start()
