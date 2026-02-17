# DigiKey MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server for the DigiKey Product Search API v4, built with [FastMCP](https://github.com/jlowin/fastmcp). Docker-first, designed for the [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/).

Originally inspired by [bengineer19/digikey_mcp](https://github.com/bengineer19/digikey_mcp).

## Prerequisites

- **DigiKey API credentials** — Register at [developer.digikey.com](https://developer.digikey.com/), create an app with `client_credentials` grant type
- **DigiKey Customer Number** — Required for order tools. Find it in your [DigiKey account settings](https://www.digikey.com/account/myaccount/).
- **Docker** (recommended) or Python 3.10+
- **Docker MCP Toolkit** — included with [Docker Desktop](https://www.docker.com/products/docker-desktop/) (requires MCP Toolkit support)

## Project Structure

```
digikey-mcp/
├── mcp_app.py               # Shared FastMCP instance
├── digikey_mcp_server.py     # Main server — authenticated tools (OAuth2)
├── digikey_noauth_tools.py   # No-auth tools (cart URL, MyList link)
├── Dockerfile                # Docker image with embedded metadata
├── server.yaml               # Registry entry for docker/mcp-registry
└── tests/                    # Unit tests
```

## Quick Start — Docker MCP Toolkit

The recommended way to run this server. The Docker MCP gateway manages the container lifecycle, injects secrets, and exposes tools to MCP clients like Claude Code or Claude Desktop.

### 1. Build the Docker image

```bash
git clone https://github.com/simon-77/digikey-mcp.git
cd digikey-mcp
docker build -t digikey-mcp:latest .
```

### 2. Create a custom catalog

The gateway discovers servers through catalog files. Create one at `~/.docker/mcp/catalogs/custom.yaml`:

```yaml
version: 3
name: custom
displayName: Custom MCP Servers
registry:
  digikey:
    description: DigiKey component search, pricing, ordering, and order status
    title: DigiKey
    type: server
    image: digikey-mcp:latest
    secrets:
      - name: digikey.CLIENT_ID
        env: CLIENT_ID
      - name: digikey.CLIENT_SECRET
        env: CLIENT_SECRET
      - name: digikey.DIGIKEY_ACCOUNT_ID
        env: DIGIKEY_ACCOUNT_ID
    env:
      - name: USE_SANDBOX
        value: "false"
      - name: DIGIKEY_LOCALE_SITE
        value: "US"
      - name: DIGIKEY_LOCALE_LANGUAGE
        value: "en"
      - name: DIGIKEY_LOCALE_CURRENCY
        value: "USD"
    tools:
      - name: keyword_search
      - name: product_details
      - name: search_manufacturers
      - name: search_categories
      - name: get_category_by_id
      - name: search_product_substitutions
      - name: get_product_media
      - name: get_product_pricing
      - name: get_digi_reel_pricing
      - name: generate_cart_url
      - name: create_mylist_link
      - name: list_orders
      - name: get_order_status
    prompts: 0
    resources: {}
```

Change the `env` values to match your locale (e.g., `AT`/`en`/`EUR` for Austria).

> **Note:** The `tools` list must match the tools defined in the server. The gateway uses this list to register tools with MCP clients. `prompts: 0` and `resources: {}` indicate the server exposes no MCP prompts or resources.

### 3. Register the catalog and enable the server

```bash
docker mcp catalog import ~/.docker/mcp/catalogs/custom.yaml
docker mcp server enable digikey
```

Re-run `catalog import` whenever you modify `custom.yaml`.

### 4. Set secrets

```bash
docker mcp secret set digikey.CLIENT_ID
docker mcp secret set digikey.CLIENT_SECRET
docker mcp secret set digikey.DIGIKEY_ACCOUNT_ID
```

You'll be prompted to enter each value. Secret names **must** be prefixed with the server name (`digikey.`).

The Account ID is your DigiKey customer number — required for order tools (`list_orders`, `get_order_status`).

### 5. Connect an MCP client

```bash
docker mcp client connect claude-code
```

This adds the gateway to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "MCP_DOCKER": {
      "command": "docker",
      "args": ["mcp", "gateway", "run"],
      "type": "stdio"
    }
  }
}
```

When the MCP client starts, the gateway launches the `digikey-mcp:latest` container, injects secrets as environment variables, and proxies tool calls.

### Rebuilding after changes

```bash
docker build -t digikey-mcp:latest .
# Restart your MCP client to pick up the new image
```

No need to re-import the catalog or re-set secrets — just rebuild and restart.

## Alternative: Docker standalone

Run the container directly without the MCP Toolkit. You manage secrets and lifecycle yourself.

```bash
docker build -t digikey-mcp .

docker run --rm -i \
  -e CLIENT_ID=your_client_id \
  -e CLIENT_SECRET=your_client_secret \
  -e DIGIKEY_ACCOUNT_ID=your_customer_number \
  -e USE_SANDBOX=false \
  -e DIGIKEY_LOCALE_SITE=US \
  -e DIGIKEY_LOCALE_LANGUAGE=en \
  -e DIGIKEY_LOCALE_CURRENCY=USD \
  digikey-mcp
```

`.mcp.json` for MCP clients:

```json
{
  "mcpServers": {
    "digikey": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "CLIENT_ID=your_client_id",
        "-e", "CLIENT_SECRET=your_client_secret",
        "-e", "DIGIKEY_ACCOUNT_ID=your_customer_number",
        "-e", "USE_SANDBOX=false",
        "-e", "DIGIKEY_LOCALE_SITE=US",
        "-e", "DIGIKEY_LOCALE_LANGUAGE=en",
        "-e", "DIGIKEY_LOCALE_CURRENCY=USD",
        "digikey-mcp"
      ]
    }
  }
}
```

Locale env vars are optional — defaults are `US`/`en`/`USD` (see [Configuration](#configuration)).

## Alternative: Standalone (pip)

Run without Docker. Requires Python 3.10+.

```bash
git clone https://github.com/simon-77/digikey-mcp.git
cd digikey-mcp
pip install .

cat > .env <<EOF
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
DIGIKEY_ACCOUNT_ID=your_customer_number
USE_SANDBOX=false
DIGIKEY_LOCALE_SITE=US
DIGIKEY_LOCALE_LANGUAGE=en
DIGIKEY_LOCALE_CURRENCY=USD
EOF

python digikey_mcp_server.py
```

`.mcp.json` for MCP clients:

```json
{
  "mcpServers": {
    "digikey": {
      "command": "python",
      "args": ["digikey_mcp_server.py"],
      "cwd": "/path/to/digikey-mcp",
      "env": {
        "CLIENT_ID": "your_client_id",
        "CLIENT_SECRET": "your_client_secret",
        "DIGIKEY_ACCOUNT_ID": "your_customer_number",
        "USE_SANDBOX": "false",
        "DIGIKEY_LOCALE_SITE": "US",
        "DIGIKEY_LOCALE_LANGUAGE": "en",
        "DIGIKEY_LOCALE_CURRENCY": "USD"
      }
    }
  }
}
```

Locale env vars are optional — defaults are `US`/`en`/`USD` (see [Configuration](#configuration)).

## Tools

### Search

| Tool | Description |
|------|-------------|
| `keyword_search` | Search products by keyword with sorting, filtering, manufacturer/category constraints |
| `search_manufacturers` | List all manufacturers |
| `search_categories` | List all product categories |
| `search_product_substitutions` | Find substitute/alternative products |

### Product Details

| Tool | Description |
|------|-------------|
| `product_details` | Full product information for a part number |
| `get_category_by_id` | Category details by ID |
| `get_product_media` | Images, documents, videos for a product |
| `get_product_pricing` | Detailed pricing with quantity breaks |
| `get_digi_reel_pricing` | DigiReel-specific pricing |

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

> **Note:** Order tools require `DIGIKEY_ACCOUNT_ID` (your DigiKey customer number). Without it, these tools return 400 Bad Request.

### Search Options

Filters (comma-separated in `search_options`): `LeadFree`, `RoHSCompliant`, `InStock`, `HasDatasheet`, `HasProductPhoto`, `Has3DModel`, `NewProduct`

Sort fields: `Packaging`, `ProductStatus`, `DigiKeyProductNumber`, `ManufacturerProductNumber`, `Manufacturer`, `MinimumQuantity`, `QuantityAvailable`, `Price`, `Supplier`, `PriceManufacturerStandardPackage`

## Configuration

All settings are controlled via environment variables. In Docker MCP Toolkit mode, these are set in the catalog `env` block or as secrets. In standalone mode, use a `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `CLIENT_ID` | *(required)* | DigiKey API client ID |
| `CLIENT_SECRET` | *(required)* | DigiKey API client secret |
| `DIGIKEY_ACCOUNT_ID` | *(optional)* | DigiKey customer number. Required for order tools (`list_orders`, `get_order_status`). |
| `USE_SANDBOX` | `true` | Use sandbox API (`true`) or production (`false`). The Dockerfile and catalog examples override this to `false`. |
| `DIGIKEY_LOCALE_SITE` | `US` | DigiKey site (e.g., `AT`, `DE`, `UK`) |
| `DIGIKEY_LOCALE_LANGUAGE` | `en` | Response language |
| `DIGIKEY_LOCALE_CURRENCY` | `USD` | Pricing currency (e.g., `EUR`) |

## Docker MCP Registry

This repo is structured for submission to the [docker/mcp-registry](https://github.com/docker/mcp-registry). The [server.yaml](server.yaml) file contains the registry entry reference — this is **not** the same as the local catalog above. When the server is published to the registry, users won't need to create a custom catalog; they'll install it directly via `docker mcp server enable digikey`.

## Troubleshooting

**Gateway shows 0 tools:** The server uses lazy OAuth initialization — it won't authenticate until the first tool call. If the gateway still shows no tools, verify the `tools` list in your catalog matches the tool names above.

**OAuth errors on first tool call:** Verify your credentials with `docker mcp secret list`. Secret names must be prefixed: `digikey.CLIENT_ID`, not `CLIENT_ID`.

**Order tools return 400 Bad Request:** The order endpoints require `DIGIKEY_ACCOUNT_ID`. Set it with `docker mcp secret set digikey.DIGIKEY_ACCOUNT_ID`. The value is your DigiKey customer number, found in your [account settings](https://www.digikey.com/account/myaccount/).

**API calls fail with 401 after running for a while:** The server fetches an OAuth token once at startup and does not refresh it. DigiKey tokens expire after ~30 minutes. Restart the MCP client (or container) to obtain a fresh token.

**Catalog changes not taking effect:** Re-run `docker mcp catalog import ~/.docker/mcp/catalogs/custom.yaml` after editing the catalog file. Restart your MCP client afterward.

## License

MIT License — see [LICENSE](LICENSE).
