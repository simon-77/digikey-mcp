import logging
from urllib.parse import urlencode

import requests

from digikey_mcp_server import mcp

logger = logging.getLogger(__name__)

FASTADD_BASE = "https://www.digikey.com/classic/ordering/fastadd.aspx"
MYLIST_THIRDPARTY_URL = "https://www.digikey.com/mylists/api/thirdparty"


def generate_cart_url(parts: list[dict], new_cart: bool = True) -> dict:
    """Generate a DigiKey FastAdd URL to populate a shopping cart.

    The returned URL, when opened in a browser, adds all parts to the
    user's DigiKey cart.

    Args:
        parts: List of dicts with keys:
            - part_number (str, required): DigiKey part number
            - quantity (int, required): Quantity to add
            - customer_ref (str, optional): Reference designator or note
        new_cart: If True, clears existing cart first (default: True)

    Returns:
        Dict with 'url' key. Adds 'warning' key if URL exceeds safe GET length.
    """
    params = {}
    for i, part in enumerate(parts, 1):
        params[f"part{i}"] = part["part_number"]
        params[f"qty{i}"] = part["quantity"]
        if part.get("customer_ref"):
            params[f"cref{i}"] = part["customer_ref"]

    if new_cart:
        params["newcart"] = "true"

    url = f"{FASTADD_BASE}?{urlencode(params)}"

    result = {"url": url}
    if len(url) > 1700:
        result["warning"] = (
            f"URL is {len(url)} chars — browser may truncate. "
            "Consider splitting into smaller batches."
        )
    return result


# Register as MCP tool (non-decorator form keeps function callable for tests)
mcp.tool()(generate_cart_url)
