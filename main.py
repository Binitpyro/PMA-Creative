"""Zeni Standalone Server (FastAPI + Uvicorn) on port 8765."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
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


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Stripe Webhook Endpoint verifying signature and logging payment events."""
    try:
        from src.business.payment import process_stripe_webhook
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        return process_stripe_webhook(payload, sig_header=sig_header)
    except ValueError as e:
        logger.warning(f"Invalid webhook payload or signature: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gumroad/webhook")
async def gumroad_webhook(request: Request):
    """Gumroad Webhook Endpoint handling form-encoded sale notifications (pings)."""
    try:
        import urllib.parse
        from src.business.payment import process_gumroad_webhook
        raw_body = await request.body()
        parsed_qs = urllib.parse.parse_qs(raw_body.decode("utf-8"))
        form_data = {k: v[0] if len(v) == 1 else v for k, v in parsed_qs.items()}
        return process_gumroad_webhook(form_data)
    except Exception as e:
        logger.error(f"Error handling Gumroad webhook ping: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def start():
    port = int(os.environ.get("ZENI_PORT", "8765"))
    host = os.environ.get("ZENI_HOST", "127.0.0.1")
    logger.info(f"Starting Zeni standalone server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start()
