import os
import json
import logging
from fastmcp import FastMCP
from dotenv import load_dotenv
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USE_SANDBOX = os.getenv("USE_SANDBOX", "true").lower() == "true"

# DigiKey OAuth2 token endpoint
if USE_SANDBOX:
    TOKEN_URL = "https://sandbox-api.digikey.com/v1/oauth2/token"
    API_BASE = "https://sandbox-api.digikey.com"
else:
    TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
    API_BASE = "https://api.digikey.com"

# Initialize FastMCP server
mcp = FastMCP("DigiKey MCP Server")

def get_access_token():
    """Get OAuth2 access token from DigiKey."""
    # Check if credentials are loaded
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("CLIENT_ID and CLIENT_SECRET must be set in .env file")
    
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    endpoint = "SANDBOX" if USE_SANDBOX else "PRODUCTION"
    logger.info(f"Requesting token from {endpoint} with CLIENT_ID: {CLIENT_ID[:10]}...")
    resp = requests.post(TOKEN_URL, data=data, headers=headers)
    
    if resp.status_code != 200:
        logger.error(f"OAuth error: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
    
    logger.info("Successfully obtained access token")
    return resp.json()["access_token"]

# Lazy token initialization — deferred to first tool call so FastMCP can
# register tools with the gateway even if OAuth credentials are missing.
logger.info("=== STARTING DIGIKEY MCP SERVER ===")
access_token = None

def _ensure_token():
    global access_token
    if access_token is None:
        access_token = get_access_token()
    return access_token

logger.info("=== SERVER READY ===")

def _get_headers(customer_id: str = "0"):
    """Get standard headers for DigiKey API requests."""
    token = _ensure_token()
    return {
        "Authorization": f"Bearer {token}",
        "X-DIGIKEY-Client-Id": CLIENT_ID,
        "Content-Type": "application/json",
        "X-DIGIKEY-Locale-Site": os.getenv("DIGIKEY_LOCALE_SITE", "US"),
        "X-DIGIKEY-Locale-Language": os.getenv("DIGIKEY_LOCALE_LANGUAGE", "en"),
        "X-DIGIKEY-Locale-Currency": os.getenv("DIGIKEY_LOCALE_CURRENCY", "USD"),
        "X-DIGIKEY-Customer-Id": customer_id,
    }

def _make_request(method: str, url: str, headers: dict, data: dict = None) -> dict:
    """Make an API request with error handling and logging."""
    logger.info(f"Making {method} request to {url}")
    logger.debug(f"Headers: {json.dumps({k: v for k, v in headers.items() if 'Authorization' not in k}, indent=2)}")
    if data:
        logger.debug(f"Request body: {json.dumps(data, indent=2)}")
    
    if method.upper() == "GET":
        resp = requests.get(url, headers=headers)
    else:
        resp = requests.post(url, headers=headers, json=data)
    
    logger.info(f"Response status: {resp.status_code}")
    if resp.status_code != 200:
        logger.error(f"API error: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
    
    return resp.json()

@mcp.tool()
def keyword_search(keywords: str, limit: int = 5, manufacturer_id: str = None, category_id: str = None, search_options: str = None, sort_field: str = None, sort_order: str = "Ascending"):
    """Search DigiKey products by keyword.
    
    Args:
        keywords: Search terms or part numbers
        limit: Maximum number of results (default: 5)
        manufacturer_id: Filter by specific manufacturer ID
        category_id: Filter by specific category ID  
        search_options: Comma-delimited filters like LeadFree,RoHSCompliant,InStock
        sort_field: Field to sort by. Options: None, Packaging, ProductStatus, DigiKeyProductNumber, ManufacturerProductNumber, Manufacturer, MinimumQuantity, QuantityAvailable, Price, Supplier, PriceManufacturerStandardPackage
        sort_order: Sort direction - Ascending or Descending (default: Ascending)
    """
    url = f"{API_BASE}/products/v4/search/keyword"
    headers = _get_headers()
    
    body = {
        "Keywords": keywords,
        "Limit": limit
    }
    
    if manufacturer_id:
        body["ManufacturerId"] = manufacturer_id
    if category_id:
        body["CategoryId"] = category_id
    if search_options:
        body["SearchOptionList"] = search_options.split(",")
    
    # Add sort options if specified
    if sort_field:
        body["SortOptions"] = {
            "Field": sort_field,
            "SortOrder": sort_order
        }
    
    return _make_request("POST", url, headers, body)

@mcp.tool()
def product_details(product_number: str, manufacturer_id: str = None, customer_id: str = "0"):
    """Get detailed information for a specific product.
    
    Args:
        product_number: DigiKey or manufacturer part number
        manufacturer_id: Optional manufacturer ID for disambiguation
        customer_id: Customer ID for pricing (default: "0")
    """
    url = f"{API_BASE}/products/v4/search/{product_number}/productdetails"
    headers = _get_headers(customer_id)
    
    params = {}
    if manufacturer_id:
        params["manufacturerId"] = manufacturer_id
    
    if params:
        url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    
    return _make_request("GET", url, headers)

@mcp.tool()
def search_manufacturers():
    """Search and retrieve all product manufacturers."""
    url = f"{API_BASE}/products/v4/search/manufacturers"
    headers = _get_headers()
    return _make_request("GET", url, headers)

@mcp.tool()
def search_categories():
    """Search and retrieve all product categories."""
    url = f"{API_BASE}/products/v4/search/categories"
    headers = _get_headers()
    return _make_request("GET", url, headers)

@mcp.tool()
def get_category_by_id(category_id: int):
    """Get specific category details by ID.
    
    Args:
        category_id: The category ID to retrieve
    """
    url = f"{API_BASE}/products/v4/search/categories/{category_id}"
    headers = _get_headers()
    return _make_request("GET", url, headers)

@mcp.tool()
def search_product_substitutions(product_number: str, limit: int = 10, search_options: str = None, exclude_marketplace: bool = False):
    """Search for product substitutions for a given product.
    
    Args:
        product_number: The product to get substitutions for
        limit: Number of substitutions (default: 10)
        search_options: Filters like LeadFree,RoHSCompliant,InStock
        exclude_marketplace: Exclude marketplace products (default: False)
    """
    url = f"{API_BASE}/products/v4/search/{product_number}/substitutions"
    headers = _get_headers()
    
    params = {"limit": limit, "excludeMarketPlaceProducts": exclude_marketplace}
    if search_options:
        params["searchOptionList"] = search_options
    
    url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    return _make_request("GET", url, headers)

@mcp.tool()
def get_product_media(product_number: str):
    """Get media (images, documents, videos) for a product.
    
    Args:
        product_number: The product to get media for
    """
    url = f"{API_BASE}/products/v4/search/{product_number}/media"
    headers = _get_headers()
    return _make_request("GET", url, headers)

@mcp.tool()
def get_product_pricing(product_number: str, customer_id: str = "0", requested_quantity: int = 1):
    """Get detailed pricing information for a product.
    
    Args:
        product_number: The product to get pricing for
        customer_id: Customer ID for pricing (default: "0")
        requested_quantity: Quantity for pricing calculation (default: 1)
    """
    url = f"{API_BASE}/products/v4/search/{product_number}/productpricing"
    headers = _get_headers(customer_id)
    
    params = {"requestedQuantity": requested_quantity}
    url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    
    return _make_request("GET", url, headers)

@mcp.tool()
def get_digi_reel_pricing(product_number: str, requested_quantity: int, customer_id: str = "0"):
    """Get DigiReel pricing for a product.
    
    Args:
        product_number: DigiKey product number (must be DigiReel compatible)
        requested_quantity: Quantity for DigiReel pricing
        customer_id: Customer ID for pricing (default: "0")
    """
    url = f"{API_BASE}/products/v4/search/{product_number}/digireelpricing"
    headers = _get_headers(customer_id)
    
    params = {"requestedQuantity": requested_quantity}
    url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    
    return _make_request("GET", url, headers)


@mcp.tool()
def list_orders(start_date: str = None, end_date: str = None, page_size: int = 10) -> dict:
    """List DigiKey orders within a date range.

    Args:
        start_date: Range start in YYYY-MM-DD format (default: 30 days ago)
        end_date: Range end in YYYY-MM-DD format (default: today)
        page_size: Results per page, max 25 (default: 10)
    """
    url = f"{API_BASE}/orderstatus/v4/orders"
    headers = _get_headers()

    params = {"PageSize": page_size}
    if start_date:
        params["StartDate"] = start_date
    if end_date:
        params["EndDate"] = end_date

    url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return _make_request("GET", url, headers)


@mcp.tool()
def get_order_status(sales_order_id: int) -> dict:
    """Get status and details of a specific DigiKey sales order.

    Args:
        sales_order_id: The sales order ID to retrieve
    """
    url = f"{API_BASE}/orderstatus/v4/salesorder/{sales_order_id}"
    headers = _get_headers()
    return _make_request("GET", url, headers)


def main():
    mcp.run()

if __name__ == "__main__":
    main() 