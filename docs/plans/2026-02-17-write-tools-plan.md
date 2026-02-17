# Write/Push Tools Extension — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 4 new MCP tools to the DigiKey server — 2 no-auth tools for pushing parts to DigiKey (MyLists link, FastAdd cart URL), and 2 order status tools using existing 2-legged OAuth.

**Architecture:** Two-file split by auth boundary. New `digikey_noauth_tools.py` for tools needing no API keys (imports `mcp` from main server). Order status tools added to existing `digikey_mcp_server.py`. No new dependencies.

**Tech Stack:** Python 3.10+, FastMCP, requests, urllib.parse (stdlib)

---

### Task 1: Create `generate_cart_url` with tests

**Files:**
- Create: `digikey_noauth_tools.py`
- Create: `tests/test_noauth_tools.py`

**Step 1: Write the failing test**

Create `tests/__init__.py` (empty) and `tests/test_noauth_tools.py`:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from digikey_noauth_tools import generate_cart_url


def test_single_part_url():
    result = generate_cart_url(
        [{"part_number": "296-8875-1-ND", "quantity": 10}]
    )
    assert "url" in result
    assert "part1=296-8875-1-ND" in result["url"]
    assert "qty1=10" in result["url"]
    assert "newcart=true" in result["url"]
    assert result["url"].startswith("https://www.digikey.com/classic/ordering/fastadd.aspx?")


def test_multiple_parts():
    result = generate_cart_url([
        {"part_number": "296-8875-1-ND", "quantity": 10, "customer_ref": "R1"},
        {"part_number": "1050-ABX00052-ND", "quantity": 1},
    ])
    assert "part1=296-8875-1-ND" in result["url"]
    assert "qty1=10" in result["url"]
    assert "cref1=R1" in result["url"]
    assert "part2=1050-ABX00052-ND" in result["url"]
    assert "qty2=1" in result["url"]
    assert "cref2" not in result["url"]


def test_no_new_cart():
    result = generate_cart_url(
        [{"part_number": "X", "quantity": 1}], new_cart=False
    )
    assert "newcart" not in result["url"]


def test_long_url_warning():
    parts = [{"part_number": f"LONGPARTNUMBER-{i}-ND", "quantity": i} for i in range(100)]
    result = generate_cart_url(parts)
    assert "warning" in result
    assert "url" in result
```

**Step 2: Run test to verify it fails**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/test_noauth_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digikey_noauth_tools'`

**Step 3: Write minimal implementation**

Create `digikey_noauth_tools.py`:

```python
import logging
from urllib.parse import urlencode

import requests

from digikey_mcp_server import mcp

logger = logging.getLogger(__name__)

FASTADD_BASE = "https://www.digikey.com/classic/ordering/fastadd.aspx"
MYLIST_THIRDPARTY_URL = "https://www.digikey.com/mylists/api/thirdparty"


@mcp.tool()
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
```

**Step 4: Run test to verify it passes**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/test_noauth_tools.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp
git add digikey_noauth_tools.py tests/
git commit -m "feat: add generate_cart_url tool with tests"
```

---

### Task 2: Add `create_mylist_link` with tests

**Files:**
- Modify: `digikey_noauth_tools.py`
- Modify: `tests/test_noauth_tools.py`

**Step 1: Write the failing test**

Append to `tests/test_noauth_tools.py`:

```python
from unittest.mock import patch, MagicMock
from digikey_noauth_tools import create_mylist_link


def test_mylist_link_builds_correct_payload():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.json.return_value = {
        "singleUseUrl": "https://www.digikey.com/mylists/singleuse/abc123"
    }

    with patch("digikey_noauth_tools.requests.post", return_value=mock_resp) as mock_post:
        result = create_mylist_link("TestList", [
            {"part_number": "296-8875-1-ND", "quantity": 10, "reference": "R1"},
        ])

    assert result == {"url": "https://www.digikey.com/mylists/singleuse/abc123"}

    call_args = mock_post.call_args
    assert "listName=TestList" in call_args[0][0]
    payload = call_args[1]["json"]
    assert len(payload) == 1
    assert payload[0]["requestedPartNumber"] == "296-8875-1-ND"
    assert payload[0]["quantities"] == [{"quantity": 10}]
    assert payload[0]["referenceDesignator"] == "R1"


def test_mylist_link_with_tags():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.json.return_value = {"singleUseUrl": "https://example.com/x"}

    with patch("digikey_noauth_tools.requests.post", return_value=mock_resp) as mock_post:
        create_mylist_link("Test", [{"part_number": "X", "quantity": 1}], tags="KiCad,ProjectX")

    assert "tags=KiCad%2CProjectX" in mock_post.call_args[0][0]


def test_mylist_link_cloudflare_block():
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.text = "<html>Cloudflare challenge</html>"

    with patch("digikey_noauth_tools.requests.post", return_value=mock_resp):
        result = create_mylist_link("Test", [{"part_number": "X", "quantity": 1}])

    assert "error" in result
    assert "Cloudflare" in result["error"] or "blocked" in result["error"].lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/test_noauth_tools.py -v -k mylist`
Expected: FAIL — `ImportError: cannot import name 'create_mylist_link'`

**Step 3: Write implementation**

Add to `digikey_noauth_tools.py` after `generate_cart_url`:

```python
@mcp.tool()
def create_mylist_link(list_name: str, parts: list[dict], tags: str = None) -> dict:
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
    return {"url": result.get("singleUseUrl", str(result))}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/test_noauth_tools.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp
git add digikey_noauth_tools.py tests/test_noauth_tools.py
git commit -m "feat: add create_mylist_link tool with tests"
```

---

### Task 3: Add Order Status tools with tests

**Files:**
- Modify: `digikey_mcp_server.py` (add tools before `main()` at line 250)
- Create: `tests/test_order_status.py`

**Step 1: Write the failing test**

Create `tests/test_order_status.py`:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from digikey_mcp_server import list_orders, get_order_status, API_BASE


def test_list_orders_default_params():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Orders": [], "TotalCount": 0}

    with patch("digikey_mcp_server._ensure_token", return_value="fake_token"), \
         patch("digikey_mcp_server.requests.get", return_value=mock_resp) as mock_get:
        result = list_orders()

    call_url = mock_get.call_args[0][0]
    assert f"{API_BASE}/orderstatus/v4/orders" in call_url
    assert "PageSize=10" in call_url
    assert result == {"Orders": [], "TotalCount": 0}


def test_list_orders_with_dates():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Orders": [], "TotalCount": 0}

    with patch("digikey_mcp_server._ensure_token", return_value="fake_token"), \
         patch("digikey_mcp_server.requests.get", return_value=mock_resp) as mock_get:
        list_orders(start_date="2026-01-01", end_date="2026-02-01")

    call_url = mock_get.call_args[0][0]
    assert "StartDate=2026-01-01" in call_url
    assert "EndDate=2026-02-01" in call_url


def test_get_order_status():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"SalesOrderId": 12345, "Status": "Shipped"}

    with patch("digikey_mcp_server._ensure_token", return_value="fake_token"), \
         patch("digikey_mcp_server.requests.get", return_value=mock_resp) as mock_get:
        result = get_order_status(12345)

    call_url = mock_get.call_args[0][0]
    assert f"{API_BASE}/orderstatus/v4/salesorder/12345" in call_url
    assert result == {"SalesOrderId": 12345, "Status": "Shipped"}
```

**Step 2: Run test to verify it fails**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/test_order_status.py -v`
Expected: FAIL — `ImportError: cannot import name 'list_orders'`

**Step 3: Write implementation**

In `digikey_mcp_server.py`, insert before `def main():` (line 250):

```python

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
```

**Step 4: Run test to verify it passes**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/test_order_status.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp
git add digikey_mcp_server.py tests/test_order_status.py
git commit -m "feat: add list_orders and get_order_status tools"
```

---

### Task 4: Wire up noauth tools import in main server

**Files:**
- Modify: `digikey_mcp_server.py` (add import after line 30)

**Step 1: Write the failing test**

Create `tests/test_tool_registration.py`:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from digikey_mcp_server import mcp


def test_all_tools_registered():
    tool_names = [t.name for t in mcp._tool_manager.list_tools()]
    # Existing tools
    assert "keyword_search" in tool_names
    assert "product_details" in tool_names
    # New no-auth tools (registered via import)
    assert "generate_cart_url" in tool_names
    assert "create_mylist_link" in tool_names
    # New order status tools
    assert "list_orders" in tool_names
    assert "get_order_status" in tool_names
```

**Step 2: Run test to verify it fails**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/test_tool_registration.py -v`
Expected: FAIL — `generate_cart_url` and `create_mylist_link` not in tool list (noauth module not imported yet)

**Step 3: Add the import**

In `digikey_mcp_server.py`, add after line 30 (`mcp = FastMCP("DigiKey MCP Server")`):

```python
import digikey_noauth_tools  # noqa: E402, F401 — registers no-auth tools on mcp
```

**Step 4: Run test to verify it passes**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/test_tool_registration.py -v`
Expected: PASS

Note: The exact attribute path for listing tools may differ across FastMCP versions. If `mcp._tool_manager.list_tools()` doesn't work, check `mcp.list_tools()` or `mcp._tools`. Adapt the test accordingly.

**Step 5: Commit**

```bash
cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp
git add digikey_mcp_server.py tests/test_tool_registration.py
git commit -m "feat: wire up noauth tools import in main server"
```

---

### Task 5: Update Dockerfile

**Files:**
- Modify: `Dockerfile` (line 3)

**Step 1: Edit Dockerfile**

Change line 3 from:
```dockerfile
COPY digikey_mcp_server.py .
```
To:
```dockerfile
COPY *.py .
```

Also update the LABEL metadata to include new tool names. Replace the `tools` portion of the JSON in the LABEL with all 13 tools.

**Step 2: Verify build**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && docker build -t digikey-mcp:latest .`
Expected: Build succeeds

**Step 3: Commit**

```bash
cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp
git add Dockerfile
git commit -m "build: copy all .py files to support multi-file server"
```

---

### Task 6: Update Docker MCP catalog and server.yaml

**Files:**
- Modify: `~/.docker/mcp/catalogs/custom.yaml` (add tool names after line 33)
- Modify: `server.yaml`

**Step 1: Edit custom.yaml**

Add after line 33 (`- name: get_digi_reel_pricing`):
```yaml
      - name: generate_cart_url
      - name: create_mylist_link
      - name: list_orders
      - name: get_order_status
```

**Step 2: Edit server.yaml**

Update description to mention ordering tools. No structural changes needed — `server.yaml` doesn't list individual tools (that's the catalog's job).

**Step 3: Re-import catalog**

Run: `docker mcp catalog import ~/.docker/mcp/catalogs/custom.yaml`
Expected: Success

**Step 4: Commit**

```bash
cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp
git add server.yaml
git commit -m "build: update catalog and server.yaml for new tools"
```

Note: `custom.yaml` is outside the repo — no git add needed.

---

### Task 7: Version bump and README update

**Files:**
- Modify: `pyproject.toml` (line 3: version)
- Modify: `README.md` (tools table + catalog example)

**Step 1: Bump version**

In `pyproject.toml`, change line 3:
```toml
version = "0.2.0"
```

Also update description:
```toml
description = "DigiKey MCP Server for product search, ordering, and order status"
```

**Step 2: Update README.md**

After the "Product Details" tools table (line 225), add:

```markdown
### Write / Push

| Tool | Description |
|------|-------------|
| `generate_cart_url` | Build a FastAdd URL to populate the DigiKey shopping cart |
| `create_mylist_link` | Create a single-use URL to import parts into DigiKey MyLists |

### Order Status

| Tool | Description |
|------|-------------|
| `list_orders` | List orders within a date range (last 30 days default) |
| `get_order_status` | Get full details of a specific sales order |
```

Update the catalog example YAML in the README to include the 4 new tool names.

**Step 3: Run all tests**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp
git add pyproject.toml README.md
git commit -m "docs: update README and bump to v0.2.0"
```

---

### Task 8: Final verification

**Step 1: Run full test suite**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 2: Docker build**

Run: `cd /home/simon/Nextcloud/Aster/Agents/MCP/dev/digikey-mcp && docker build -t digikey-mcp:latest .`
Expected: Build succeeds

**Step 3: Quick smoke test in container**

Run: `docker run --rm -i digikey-mcp:latest python -c "from digikey_mcp_server import mcp; print([t.name for t in mcp._tool_manager.list_tools()])"`
Expected: List of 13 tool names including all 4 new ones.

Note: The import check command may need adapting based on FastMCP's internal API. If `_tool_manager` doesn't exist, try `mcp.list_tools()` or just verify the import succeeds without errors:
`docker run --rm digikey-mcp:latest python -c "import digikey_mcp_server; import digikey_noauth_tools; print('OK')"`
