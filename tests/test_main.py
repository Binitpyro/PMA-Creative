"""Unit tests for main.py FastAPI routes and endpoints."""
from __future__ import annotations

from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_signup_endpoint():
    signup_payload = {
        "name": "Alex Vance",
        "email": "alex@vfx.com",
        "organization": "VFX Lab",
        "use_case": "FLIP solver optimization",
    }

    mock_triage_res = {
        "status": "success",
        "name": "Alex Vance",
        "recommended_tier": "Freelancer Tier",
        "reasoning": "Standard artist evaluation.",
        "onboarding_note": "Welcome to Zeni!",
        "stripe_checkout_url": "https://checkout.stripe.com/test",
    }

    with patch("src.business.triage.triage_trial_signup", return_value=mock_triage_res):
        response = client.post("/api/signup", json=signup_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["stripe_checkout_url"] == "https://checkout.stripe.com/test"


def test_stripe_webhook_endpoint():
    webhook_payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_email": "payer@vfx.com",
                "amount_total": 2900,
            }
        }
    }

    with patch("src.business.store.log_agent_decision"):
        response = client.post("/api/stripe/webhook", json=webhook_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["processed"] is True


def test_gumroad_webhook_endpoint():
    form_data = {
        "seller_id": "seller_test",
        "product_name": "PMA Creative Module — Freelancer Tier",
        "email": "gumbuyer@vfx.com",
        "price": "2900",
    }

    with patch("src.business.store.log_agent_decision"):
        response = client.post("/api/gumroad/webhook", data=form_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["processed"] is True
        assert data["customer"] == "gumbuyer@vfx.com"
