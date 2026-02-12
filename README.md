# DigiKey MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server for the DigiKey Product Search API v4, built with [FastMCP](https://github.com/jlowin/fastmcp). Docker-first, designed for the [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/).

Originally inspired by [bengineer19/digikey_mcp](https://github.com/bengineer19/digikey_mcp).

## Prerequisites

- DigiKey API credentials ([client_credentials grant](https://developer.digikey.com/))
- Docker (recommended) or Python 3.10+

## Quick Start

### Docker MCP Toolkit (recommended)

```bash
# Build image
docker build -t digikey-mcp .

# Set secrets
docker mcp secret set digikey.CLIENT_ID
docker mcp secret set digikey.CLIENT_SECRET

# Add catalog and enable
docker mcp catalog import your-catalog.yaml
docker mcp server enable digikey

# Connect to your MCP client
docker mcp client connect claude-code
```

See [server.yaml](server.yaml) for the catalog entry reference.

### Docker (standalone container)

```bash
docker build -t digikey-mcp .

docker run --rm -i \
  -e CLIENT_ID=your_client_id \
  -e CLIENT_SECRET=your_client_secret \
  -e USE_SANDBOX=false \
  digikey-mcp
```

### MCP Client Config (Docker)

Add to your `.mcp.json` or Claude Desktop config:

```json
{
  "mcpServers": {
    "digikey": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "CLIENT_ID=your_client_id",
        "-e", "CLIENT_SECRET=your_client_secret",
        "-e", "USE_SANDBOX=false",
        "digikey-mcp"
      ]
    }
  }
}
```

### Standalone (pip/uv)

```bash
git clone https://github.com/simon-77/digikey-mcp.git
cd digikey-mcp
pip install fastmcp requests python-dotenv

cat > .env <<EOF
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
USE_SANDBOX=false
EOF

python digikey_mcp_server.py
```

`.mcp.json` for standalone:

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
        "USE_SANDBOX": "false"
      }
    }
  }
}
```

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

### Search Options

Filters (comma-separated in `search_options`): `LeadFree`, `RoHSCompliant`, `InStock`, `HasDatasheet`, `HasProductPhoto`, `Has3DModel`, `NewProduct`

Sort fields: `Packaging`, `ProductStatus`, `DigiKeyProductNumber`, `ManufacturerProductNumber`, `Manufacturer`, `MinimumQuantity`, `QuantityAvailable`, `Price`, `Supplier`, `PriceManufacturerStandardPackage`

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CLIENT_ID` | *(required)* | DigiKey API client ID |
| `CLIENT_SECRET` | *(required)* | DigiKey API client secret |
| `USE_SANDBOX` | `true` | Use sandbox API (`true`) or production (`false`) |
| `DIGIKEY_LOCALE_SITE` | `US` | DigiKey site (e.g., `AT`, `DE`, `UK`) |
| `DIGIKEY_LOCALE_LANGUAGE` | `en` | Response language |
| `DIGIKEY_LOCALE_CURRENCY` | `USD` | Pricing currency (e.g., `EUR`) |

## Docker MCP Registry

This repo is structured for submission to the [docker/mcp-registry](https://github.com/docker/mcp-registry). The [server.yaml](server.yaml) file contains the catalog entry reference — adapt it when submitting a PR to the registry.

Key requirements met:
- `Dockerfile` with `io.docker.server.metadata` label
- Secrets declared for `CLIENT_ID` and `CLIENT_SECRET`
- Configurable locale via environment variables

## License

MIT License — see [LICENSE](LICENSE).
