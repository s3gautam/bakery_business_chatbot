"""Thin HTTP client the Streamlit UI uses to talk to the FastAPI backend.

Kept separate from the backend's own `app.ssl_utils` module (Streamlit
runs as its own process) but follows the same corporate-SSL-interception
policy described in CLAUDE.md: prefer a CA bundle, fall back to an
explicit local-dev-only bypass flag, never disable verification by
default.
"""

import os

import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
_CA_BUNDLE = os.environ.get("REQUESTS_CA_BUNDLE")
_DEV_DISABLE_SSL_VERIFY = os.environ.get("DEV_DISABLE_SSL_VERIFY", "false").lower() == "true"


def _verify() -> str | bool:
    if _CA_BUNDLE:
        return _CA_BUNDLE
    if _DEV_DISABLE_SSL_VERIFY:
        return False
    return True


def _client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE_URL, verify=_verify(), timeout=30.0)


def send_chat_message(conversation_id: str, message: str) -> dict:
    with _client() as client:
        response = client.post(
            "/chat", json={"conversation_id": conversation_id, "message": message}
        )
        response.raise_for_status()
        return response.json()


def get_config() -> dict:
    with _client() as client:
        response = client.get("/config")
        response.raise_for_status()
        return response.json()


def update_config(payload: dict) -> dict:
    with _client() as client:
        response = client.put("/config", json=payload)
        response.raise_for_status()
        return response.json()


def get_menu() -> list[dict]:
    with _client() as client:
        response = client.get("/menu")
        response.raise_for_status()
        return response.json()
