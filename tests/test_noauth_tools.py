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
