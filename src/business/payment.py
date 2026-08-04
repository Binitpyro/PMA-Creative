"""Payment Integration (Gumroad & Stripe) & Webhook Handler for Zeni Business Module."""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

from src.business.store import log_agent_decision

logger = logging.getLogger("zeni.business.payment")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
GUMROAD_PRODUCT_URL = os.environ.get(
    "GUMROAD_CHECKOUT_URL", "https://gumroad.com/l/zeni_creative_freelancer"
)
DEFAULT_CHECKOUT_URL = os.environ.get(
    "CHECKOUT_URL", GUMROAD_PRODUCT_URL
)


def create_checkout_session(
    tier: str = "Freelancer Tier",
    customer_email: str = "",
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> dict[str, Any]:
    """Create a Checkout Session or return configured payment URL (Gumroad/Stripe)."""
    if STRIPE_SECRET_KEY:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                customer_email=customer_email if customer_email else None,
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"PMA Creative Module — {tier}",
                            "description": "Monthly subscription for Zeni Houdini Assistant",
                        },
                        "unit_amount": 2900,  # $29.00
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url or "https://pma-creative.ai/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url or "https://pma-creative.ai/cancel",
            )
            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "tier": tier,
                "provider": "stripe",
                "livemode": session.livemode,
            }
        except Exception as e:
            logger.warning(f"Stripe API call failed: {e}. Falling back to default checkout URL.")

    # Fallback to configured Gumroad or direct checkout URL
    checkout_url = DEFAULT_CHECKOUT_URL
    if customer_email:
        sep = "&" if "?" in checkout_url else "?"
        checkout_url = f"{checkout_url}{sep}email={customer_email}"

    return {
        "checkout_url": checkout_url,
        "session_id": "cs_test_mock_session_id",
        "tier": tier,
        "provider": "gumroad",
        "livemode": False,
    }


def process_gumroad_webhook(form_data: dict[str, Any]) -> dict[str, Any]:
    """Process incoming form-encoded Gumroad ping/webhook and log payment decision."""
    seller_id = form_data.get("seller_id", "")
    product_name = form_data.get("product_name", "PMA Creative Module")
    buyer_email = form_data.get("email") or form_data.get("buyer_email", "unknown@domain.com")
    price_cents = form_data.get("price", "0")

    try:
        amount_usd = float(price_cents) / 100.0 if float(price_cents) > 100 else float(price_cents)
    except Exception:
        amount_usd = 0.0

    decision_data = {
        "event_type": "gumroad_ping",
        "product_name": product_name,
        "customer_email": buyer_email,
        "amount_paid_usd": amount_usd,
        "seller_id": seller_id,
        "status": "payment_confirmed",
    }

    log_agent_decision(
        kind="gumroad_payment_processed",
        input_summary=f"Gumroad Ping: {product_name} | Buyer: {buyer_email} | Amount: ${amount_usd:.2f}",
        decision=decision_data,
        provider="gumroad_webhook",
        model="automated_billing",
        latency_ms=0.0,
    )

    return {
        "status": "success",
        "processed": True,
        "event": "gumroad_ping",
        "customer": buyer_email,
        "amount_usd": amount_usd,
    }


def process_stripe_webhook(
    payload: bytes,
    sig_header: Optional[str] = None,
    webhook_secret: Optional[str] = None,
) -> dict[str, Any]:
    """Process incoming Stripe webhook event and log payment decision."""
    secret = webhook_secret or STRIPE_WEBHOOK_SECRET
    event_data = {}

    if secret and sig_header and STRIPE_SECRET_KEY:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
            event_data = event.to_dict()
        except Exception as e:
            logger.error(f"Stripe signature verification failed: {e}")
            raise ValueError(f"Webhook signature verification failed: {e}") from e
    else:
        try:
            event_data = json.loads(payload.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e

    event_type = event_data.get("type", "unknown_event")
    data_object = event_data.get("data", {}).get("object", {})

    if event_type in {"checkout.session.completed", "invoice.payment_succeeded"}:
        customer_email = data_object.get("customer_email") or data_object.get("customer_details", {}).get("email", "unknown")
        amount_total = data_object.get("amount_total", 0) / 100.0

        decision_data = {
            "event_type": event_type,
            "customer_email": customer_email,
            "amount_paid_usd": amount_total,
            "status": "payment_confirmed",
        }

        log_agent_decision(
            kind="stripe_payment_processed",
            input_summary=f"Stripe Event: {event_type} | Customer: {customer_email} | Amount: ${amount_total:.2f}",
            decision=decision_data,
            provider="stripe_webhook",
            model="automated_billing",
            latency_ms=0.0,
        )

        return {"status": "success", "processed": True, "event": event_type, "customer": customer_email}

    return {"status": "success", "processed": False, "event": event_type}
