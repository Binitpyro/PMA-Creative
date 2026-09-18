"""Payment & License Validation Integration (Gumroad) for Zeni."""
from __future__ import annotations

import logging
import os
import httpx
from typing import Optional

logger = logging.getLogger("zeni.business.payment")

# Core runs on 8000 usually
CORE_API_URL = os.environ.get("PMA_CORE_URL", "http://127.0.0.1:8000")
GUMROAD_PRODUCT_URL = os.environ.get(
    "GUMROAD_CHECKOUT_URL", "https://gumroad.com/l/zeni_creative_freelancer"
)

def get_checkout_url(customer_email: str = "") -> str:
    """Return the configured Gumroad checkout URL."""
    checkout_url = GUMROAD_PRODUCT_URL
    if customer_email:
        sep = "&" if "?" in checkout_url else "?"
        checkout_url = f"{checkout_url}{sep}email={customer_email}"
    return checkout_url

def validate_license(license_key: str) -> Optional[str]:
    """
    Validates a Gumroad license key against the Core API.
    Returns a JWT session token if valid, None otherwise.
    """
    try:
        response = httpx.post(
            f"{CORE_API_URL}/api/licenses/validate", 
            json={"license_key": license_key},
            timeout=5.0
        )
        response.raise_for_status()
        data = response.json()
        return data.get("jwt")
    except Exception as e:
        logger.error(f"Failed to validate license with Core: {e}")
        return None
