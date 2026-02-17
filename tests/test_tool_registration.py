import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from digikey_mcp_server import mcp


def test_all_tools_registered():
    tool_names = list(asyncio.run(mcp.get_tools()).keys())
    # Existing tools
    assert "keyword_search" in tool_names
    assert "product_details" in tool_names
    # New no-auth tools (registered via import)
    assert "generate_cart_url" in tool_names
    assert "create_mylist_link" in tool_names
    # New order status tools
    assert "list_orders" in tool_names
    assert "get_order_status" in tool_names
