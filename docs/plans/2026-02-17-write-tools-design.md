# DigiKey MCP Server — Write/Push Tools Extension Design

## Problem

The DigiKey MCP server currently only supports read-only product search (9 tools). There's no way for an agent to push a curated parts list to DigiKey after resolving a BOM from a KiCad schematic. The user must manually copy part numbers into DigiKey.

## Goal

Enable the workflow: **KiCad BOM → agent resolves parts → push to DigiKey for user review/purchase**.

## Scope

4 new tools, split into two categories:

### No-Auth Tools (new file: `digikey_noauth_tools.py`)

**1. `generate_cart_url(parts, new_cart=True)`**
- Pure URL construction — zero network calls
- Builds DigiKey FastAdd URL: `https://www.digikey.com/classic/ordering/fastadd.aspx?part1=X&qty1=N...`
- Input: `[{part_number, quantity, customer_ref?}]`
- Output: `{"url": "...", "warning?": "..."}`  (warning if URL > 1700 chars)
- Use case: direct-to-cart for quick purchases

**2. `create_mylist_link(list_name, parts, tags=None)`**
- POST to `https://www.digikey.com/mylists/api/thirdparty`
- Input: list name + `[{part_number, quantity, reference?, notes?, manufacturer?}]`
- Output: `{"url": "https://...singleuse/..."}` — user clicks to import into their DigiKey account
- Custom User-Agent to avoid Cloudflare WAF
- Cloudflare HTML detection with clear error message
- Use case: save-for-review before purchasing

### Auth Tools (added to existing `digikey_mcp_server.py`)

**3. `list_orders(start_date=None, end_date=None, page_size=10)`**
- GET `{API_BASE}/orderstatus/v4/orders`
- Uses existing 2-legged OAuth via `_get_headers` + `_make_request`
- Default: last 30 days, 10 results per page

**4. `get_order_status(sales_order_id)`**
- GET `{API_BASE}/orderstatus/v4/salesorder/{id}`
- Uses existing 2-legged OAuth
- Returns full order with line items + shipping

## Architecture Decision: Two-File Split

Split by auth boundary:
- `digikey_mcp_server.py` — all OAuth-dependent tools (existing 9 + 2 new order status)
- `digikey_noauth_tools.py` — tools that need no API keys at all

Rationale:
- No-auth file has zero coupling to credentials/secrets
- If only no-auth tools are used, OAuth token is never requested
- Clear conceptual boundary for future maintenance
- The no-auth file imports `mcp` from main server to register on same FastMCP instance

## Deployment Changes

- Dockerfile: `COPY *.py .` (was single file copy)
- Docker MCP catalog: add 4 tool names to `custom.yaml`
- Version: `0.2.0`

## Out of Scope

- 3-legged OAuth (needed for Quote API, full MyLists CRUD)
- Product Change Notifications (deferred to next round)
- Bonded Inventory (dropped)
- KiCad ↔ DigiKey code coupling (agent orchestrates)
