from __future__ import annotations

import os
from typing import Any

SERPER_API_KEY_ENV = "SERPER_API_KEY"
SERPER_BASE_URL = "https://google.serper.dev"
SERPER_ENDPOINTS = {
    "search",
    "images",
    "videos",
    "places",
    "maps",
    "reviews",
    "news",
    "shopping",
    "lens",
    "scholar",
    "patents",
    "autocomplete",
}


def _error_response(message: str, **extra: Any) -> dict[str, Any]:
    """Helper to format uniform error payloads."""
    return {"status": "error", "message": message, **extra}


def google_search(
    endpoint: str,
    q: str | None = None,
    url: str | None = None,
    image_url: str | None = None,
    gl: str = "in",
    hl: str | None = None,
    location: str | None = None,
    num: int | None = None,
    page: int | None = None,
    autocorrect: bool | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    """
    Execute a unified query against the Google Serper API endpoints.

    Args:
        endpoint: Serper route to target. Supported values are search, images,
            videos, places, maps, reviews, news, shopping, lens, scholar,
            patents, and autocomplete.
        q: Search query. Required for every endpoint except lens.
        url: Public image URL for the lens endpoint.
        image_url: Alias for url, accepted for lens requests.
        gl: Country code. Defaults to in.
        hl: Language code.
        location: Optional location framing.
        num: Optional number of results.
        page: Optional pagination page.
        autocorrect: Optional query autocorrect toggle.
        timeout_seconds: HTTP request timeout in seconds.
    """
    api_key = os.getenv(SERPER_API_KEY_ENV)
    if not api_key:
        return _error_response(f"Missing environment variable: {SERPER_API_KEY_ENV}")

    if endpoint not in SERPER_ENDPOINTS:
        return _error_response(
            "Unsupported Serper endpoint.",
            endpoint=endpoint,
            supported_endpoints=sorted(SERPER_ENDPOINTS),
        )

    try:
        import requests
    except ImportError:
        return _error_response("Missing dependency: requests")

    lens_url = url or image_url

    payload = {
        key: value
        for key, value in {
            "q": q,
            "url": lens_url,
            "gl": gl,
            "hl": hl,
            "location": location,
            "num": num,
            "page": page,
            "autocorrect": autocorrect,
        }.items()
        if value is not None and value != ""
    }

    if endpoint == "lens" and "url" not in payload:
        return _error_response("Missing required parameter: 'url' for 'lens' endpoint.")
    if endpoint != "lens" and "q" not in payload:
        return _error_response(f"Missing required parameter: 'q' for '{endpoint}' endpoint.")

    request_url = f"{SERPER_BASE_URL}/{endpoint}"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            request_url,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        response_obj = getattr(exc, "response", None)
        body = response_obj.text[:1000] if response_obj is not None else None
        status_code = response_obj.status_code if response_obj is not None else None
        return _error_response(
            str(exc),
            endpoint=endpoint,
            status_code=status_code,
            response_text=body,
        )

    try:
        data = response.json()
    except ValueError:
        return _error_response(
            "Serper returned a non-JSON response.",
            endpoint=endpoint,
            response_text=response.text[:1000],
        )

    return {
        "status": "success",
        "endpoint": endpoint,
        "payload": payload,
        "data": data,
    }
