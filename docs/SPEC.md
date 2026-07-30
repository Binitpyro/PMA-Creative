# XPrize Creative Module - Bootstrap Specification (Updated)

This document provides all the necessary context, architecture, and project structure to bootstrap the **XPrize Creative Module** in a completely separate repository. 

---

> [!IMPORTANT]
> **Core Objective**
> The XPrize Creative Module is a standalone client application (sidecar) that connects to the Personal Memory Assistant (PMA) Core. It leverages the PMA Core's retrieval capabilities while operating in its own isolated memory space to handle specialized, high-temperature "creative" LLM generation tasks specifically for the XPrize requirements.

## 1. Connection Architecture

The PMA Core (v0.0.70) exposes a secure WebSocket endpoint designed specifically for external modules.

*   **Protocol:** WebSocket (`ws://` or `wss://`)
*   **Endpoint:** `/api/modules/ws` *(Confirmed against `main.py` and `tests/test_modules_ws.py`)*
*   **Authentication:** Requires the `X_LOCAL_ACCESS_TOKEN`. This token must match the one running in the PMA Core.
    *   *Method 1 (Preferred):* Pass as an HTTP Header: `x-local-access-token: <TOKEN>`
    *   *Method 2 (Fallback):* Pass as a query parameter: `?token=<TOKEN>`

### 1.1 Secret Handling (CRITICAL)

> [!CAUTION]
> Do NOT store `X_LOCAL_ACCESS_TOKEN` in a plaintext `.env` file. The PMA Core uses the OS Keyring to load this secret securely. The Creative Module must do the same.

Use the Python `keyring` library to retrieve the token on boot:
```python
import keyring
token = keyring.get_password("PersonalMemoryAssistant", "X_LOCAL_ACCESS_TOKEN")
```

### 1.2 Message Envelope & Missing Contract

Currently, the PMA Core only implements a `ping` action. Any other action is simply echoed back. **The contract for context retrieval does not exist yet and must be built on the PMA Core side concurrently with this client.**

**Proposed Contract Schema (JSON-RPC 2.0 style):**
*Client Request (Search):*
```json
{
  "action": "search",
  "query": "XPrize context regarding X",
  "limit": 5
}
```
*Core Response (Streaming vs Single-Shot):*
```json
{
  "status": "success",
  "action": "search",
  "data": {
    "results": [
      {"chunk": "...", "score": 0.9}
    ]
  }
}
```
*Note: Ensure the new agent explicitly defines and agrees upon this schema with the PMA Core before writing the client.*

---

## 2. Recommended Project Structure

```text
xprize-creative-module/
├── requirements.txt         # websockets, pydantic, httpx, keyring
├── main.py                  # Application entrypoint & CLI
├── src/
│   ├── __init__.py
│   ├── client/
│   │   ├── __init__.py
│   │   └── pma_ws_client.py # Manages the persistent WebSocket connection to PMA Core
│   ├── core/
│   │   ├── __init__.py
│   │   └── xprize_agent.py  # The LLM / Creative generation logic
│   └── models/
│       ├── __init__.py
│       └── schemas.py       # Pydantic models for the WS JSON envelopes
└── README.md
```
