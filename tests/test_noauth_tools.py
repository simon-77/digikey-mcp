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
