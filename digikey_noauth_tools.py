import logging
from urllib.parse import urlencode

import requests

from mcp_app import mcp

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


def create_mylist_link(list_name: str, parts: list[dict], tags: str | None = None) -> dict:
    """Create a DigiKey MyList import link via the third-party API.

    Returns a single-use URL. When the user opens it, the parts are
    imported into their DigiKey MyLists account. No API credentials needed.

    Args:
        list_name: Name for the new list
        parts: List of dicts with keys:
            - part_number (str, required): DigiKey or manufacturer part number
            - quantity (int, required): Quantity needed
            - reference (str, optional): Reference designator (e.g., "R1")
            - notes (str, optional): Additional notes
            - manufacturer (str, optional): Manufacturer name
        tags: Optional comma-separated tags (e.g., "KiCad,ProjectX")

    Returns:
        Dict with 'url' key containing the single-use import URL,
        or 'error' key if the request was blocked.
    """
    params = {"listName": list_name}
    if tags:
        params["tags"] = tags

    url = f"{MYLIST_THIRDPARTY_URL}?{urlencode(params)}"

    payload = []
    for part in parts:
        payload.append({
            "requestedPartNumber": part["part_number"],
            "manufacturerName": part.get("manufacturer", ""),
            "referenceDesignator": part.get("reference", ""),
            "customerReference": part.get("customer_ref", ""),
            "notes": part.get("notes", ""),
            "quantities": [{"quantity": part["quantity"]}],
        })

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "digikey-mcp/0.2.0",
    }

    logger.info(f"Creating MyList link: {list_name} with {len(parts)} parts")
    resp = requests.post(url, json=payload, headers=headers)

    if resp.status_code != 200:
        logger.error(f"MyList API error: {resp.status_code} - {resp.text}")
        if "text/html" in resp.headers.get("Content-Type", ""):
            return {"error": "Request blocked (likely Cloudflare WAF). Try again later."}
        resp.raise_for_status()

    result = resp.json()
    # API returns a plain JSON string (the URL), not an object
    if isinstance(result, str):
        return {"url": result}
    return {"url": result.get("singleUseUrl", str(result))}


mcp.tool()(create_mylist_link)
