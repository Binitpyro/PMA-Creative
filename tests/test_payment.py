"""Unit tests for payment processing (Gumroad & Stripe in src/business/payment.py)."""
from __future__ import annotations

import json
from unittest.mock import patch

from src.business.payment import create_checkout_session, process_gumroad_webhook, process_stripe_webhook


def test_create_checkout_session_default_fallback():
    res = create_checkout_session(tier="Studio Tier", customer_email="studio@vfx.com")
    assert "checkout_url" in res
    assert res["tier"] == "Studio Tier"
    assert res["livemode"] is False


def test_process_gumroad_webhook_ping():
    form_data = {
        "seller_id": "seller_123",
        "product_name": "PMA Creative Module — Freelancer Tier",
        "email": "artist@vfx.com",
        "price": "2900",
    }

    with patch("src.business.payment.log_agent_decision") as mock_log:
        res = process_gumroad_webhook(form_data)
        assert res["status"] == "success"
        assert res["processed"] is True
        assert res["customer"] == "artist@vfx.com"
        assert res["amount_usd"] == 29.0
        assert mock_log.called


def test_process_stripe_webhook_completed_event():
    payload = json.dumps({
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_email": "artist@vfx.com",
                "amount_total": 4900,
            }
        }
    }).encode("utf-8")

    with patch("src.business.payment.log_agent_decision") as mock_log:
        res = process_stripe_webhook(payload)
        assert res["status"] == "success"
        assert res["processed"] is True
        assert res["customer"] == "artist@vfx.com"
        assert mock_log.called
