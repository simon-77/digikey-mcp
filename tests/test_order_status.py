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
        result = list_orders.fn()

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
        list_orders.fn(start_date="2026-01-01", end_date="2026-02-01")

    call_url = mock_get.call_args[0][0]
    assert "StartDate=2026-01-01" in call_url
    assert "EndDate=2026-02-01" in call_url


def test_get_order_status():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"SalesOrderId": 12345, "Status": "Shipped"}

    with patch("digikey_mcp_server._ensure_token", return_value="fake_token"), \
         patch("digikey_mcp_server.requests.get", return_value=mock_resp) as mock_get:
        result = get_order_status.fn(12345)

    call_url = mock_get.call_args[0][0]
    assert f"{API_BASE}/orderstatus/v4/salesorder/12345" in call_url
    assert result == {"SalesOrderId": 12345, "Status": "Shipped"}
