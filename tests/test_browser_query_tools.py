from src.tools.browser_query_tools import (
    VALID_WAIT_UNTIL,
    _error_response,
    _parse_strip_selectors,
    open_url_and_capture_html,
    open_url_and_capture_html_with_local_browser,
)


def test_error_response_format():
    result = _error_response("something broke")
    assert result == {"status": "error", "message": "something broke"}


def test_parse_strip_selectors_none():
    assert _parse_strip_selectors(None) is None


def test_parse_strip_selectors_csv():
    assert _parse_strip_selectors("script, .ads, #popup") == [
        "script",
        ".ads",
        "#popup",
    ]


def test_parse_strip_selectors_empty_string():
    assert _parse_strip_selectors("") is None


def test_parse_strip_selectors_whitespace_only():
    assert _parse_strip_selectors("  ,  , ") is None


def test_open_url_invalid_wait_until():
    result = open_url_and_capture_html(
        url="https://example.com",
        wait_until="invalid_value",
    )
    assert result["status"] == "error"
    assert "Invalid wait_until" in result["message"]


def test_open_url_local_invalid_wait_until():
    result = open_url_and_capture_html_with_local_browser(
        url="https://example.com",
        wait_until="bogus",
    )
    assert result["status"] == "error"
    assert "Invalid wait_until" in result["message"]


def test_valid_wait_until_values():
    assert VALID_WAIT_UNTIL == {"commit", "domcontentloaded", "load", "networkidle"}
