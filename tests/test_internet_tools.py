import os
from unittest.mock import MagicMock, patch

from src.tools.internet_tools import SERPER_API_KEY_ENV, google_search


def test_google_search_missing_api_key():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop(SERPER_API_KEY_ENV, None)
        result = google_search(endpoint="search", q="test")
    assert result["status"] == "error"
    assert SERPER_API_KEY_ENV in result["message"]


def test_google_search_invalid_endpoint():
    with patch.dict(os.environ, {SERPER_API_KEY_ENV: "fake-key"}):
        result = google_search(endpoint="not_real", q="test")
    assert result["status"] == "error"
    assert "Unsupported" in result["message"]
    assert "supported_endpoints" in result


def test_google_search_missing_q_for_search():
    with patch.dict(os.environ, {SERPER_API_KEY_ENV: "fake-key"}):
        result = google_search(endpoint="search")
    assert result["status"] == "error"
    assert "'q'" in result["message"]


def test_google_search_missing_url_for_lens():
    with patch.dict(os.environ, {SERPER_API_KEY_ENV: "fake-key"}):
        result = google_search(endpoint="lens", q="ignored")
    assert result["status"] == "error"
    assert "'url'" in result["message"]


def test_google_search_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {"organic": [{"title": "Example"}]}
    mock_response.raise_for_status = MagicMock()

    with (
        patch.dict(os.environ, {SERPER_API_KEY_ENV: "fake-key"}),
        patch("requests.post", return_value=mock_response) as mock_post,
    ):
        result = google_search(endpoint="search", q="hello world")

    assert result["status"] == "success"
    assert result["endpoint"] == "search"
    assert result["data"] == {"organic": [{"title": "Example"}]}
    mock_post.assert_called_once()


def test_google_search_http_error():
    import requests as req

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limited"
    exc = req.exceptions.HTTPError(response=mock_response)

    with (
        patch.dict(os.environ, {SERPER_API_KEY_ENV: "fake-key"}),
        patch("requests.post", side_effect=exc),
    ):
        result = google_search(endpoint="search", q="hello")

    assert result["status"] == "error"
    assert result["status_code"] == 429
