from __future__ import annotations

from typing import Any

from src.tools.browser_html_tools import get_page_html_content

VALID_WAIT_UNTIL = {"commit", "domcontentloaded", "load", "networkidle"}


def _error_response(message: str) -> dict[str, Any]:
    return {"status": "error", "message": message}


def _parse_strip_selectors(value: str | None) -> list[str] | None:
    if value is None:
        return None
    selectors = [item.strip() for item in value.split(",") if item.strip()]
    return selectors or None


def list_browser_pages(cdp_url: str = "http://127.0.0.1:9222") -> dict[str, Any]:
    """List open pages from a Chromium browser exposed over CDP."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(cdp_url)
            try:
                if browser.contexts:
                    context = browser.contexts[0]
                else:
                    context = browser.new_context()

                pages = []
                for index, page in enumerate(context.pages):
                    pages.append(
                        {
                            "page_index": index,
                            "url": page.url,
                            "title": page.title(),
                        }
                    )

                return {
                    "status": "success",
                    "cdp_url": cdp_url,
                    "pages": pages,
                    "count": len(pages),
                }
            finally:
                browser.close()
    except Exception as exc:
        return _error_response(str(exc))


def capture_current_browser_page_html(
    cdp_url: str = "http://127.0.0.1:9222",
    page_index: int = 0,
    root_selector: str = "body",
    include_visible_text: bool = True,
    strip_selectors: str | None = None,
    mask_passwords: bool = True,
) -> dict[str, Any]:
    """
    Capture cleaned HTML from an already open browser page over CDP.
    """
    try:
        from playwright.sync_api import sync_playwright

        selectors = _parse_strip_selectors(strip_selectors)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(cdp_url)
            try:
                if browser.contexts:
                    context = browser.contexts[0]
                else:
                    context = browser.new_context()

                if not context.pages:
                    return _error_response("No open browser pages found in the connected context.")

                if page_index < 0 or page_index >= len(context.pages):
                    return _error_response(
                        f"Invalid page_index {page_index}. Available pages: 0 to {len(context.pages) - 1}."
                    )

                page = context.pages[page_index]
                snapshot = get_page_html_content(
                    page,
                    root_selector=root_selector,
                    include_form_values=True,
                    include_visible_text=include_visible_text,
                    strip_selectors=selectors,
                    mask_passwords=mask_passwords,
                )
                return {
                    "status": "success",
                    "cdp_url": cdp_url,
                    "page_index": page_index,
                    **snapshot,
                }
            finally:
                browser.close()
    except Exception as exc:
        return _error_response(str(exc))


def open_url_and_capture_html(
    url: str,
    cdp_url: str = "http://127.0.0.1:9222",
    page_index: int = 0,
    root_selector: str = "body",
    wait_until: str = "domcontentloaded",
    timeout_ms: int = 30000,
    include_visible_text: bool = True,
    strip_selectors: str | None = None,
    mask_passwords: bool = True,
) -> dict[str, Any]:
    """
    Open a URL in an existing browser page over CDP and capture cleaned HTML.
    """
    if wait_until not in VALID_WAIT_UNTIL:
        return _error_response(
            f"Invalid wait_until value '{wait_until}'. "
            f"Supported: {', '.join(sorted(VALID_WAIT_UNTIL))}."
        )

    try:
        from playwright.sync_api import sync_playwright

        selectors = _parse_strip_selectors(strip_selectors)
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(cdp_url)
            try:
                if browser.contexts:
                    context = browser.contexts[0]
                else:
                    context = browser.new_context()

                if page_index < 0:
                    return _error_response(
                        f"Invalid page_index {page_index}. Must be >= 0."
                    )

                if page_index < len(context.pages):
                    page = context.pages[page_index]
                    created_page = False
                else:
                    page = context.new_page()
                    created_page = True

                try:
                    page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                    snapshot = get_page_html_content(
                        page,
                        root_selector=root_selector,
                        include_form_values=True,
                        include_visible_text=include_visible_text,
                        strip_selectors=selectors,
                        mask_passwords=mask_passwords,
                    )
                    return {
                        "status": "success",
                        "cdp_url": cdp_url,
                        "page_index": page_index,
                        "navigated_to": url,
                        **snapshot,
                    }
                finally:
                    if created_page:
                        page.close()
            finally:
                browser.close()
    except Exception as exc:
        return _error_response(str(exc))


def open_url_and_capture_html_with_local_browser(
    url: str,
    root_selector: str = "body",
    wait_until: str = "domcontentloaded",
    timeout_ms: int = 30000,
    include_visible_text: bool = True,
    strip_selectors: str | None = None,
    mask_passwords: bool = True,
    headless: bool = True,
) -> dict[str, Any]:
    """
    Launch a temporary local browser, open a URL, capture cleaned HTML, and close the browser.
    """
    if wait_until not in VALID_WAIT_UNTIL:
        return _error_response(
            f"Invalid wait_until value '{wait_until}'. "
            f"Supported: {', '.join(sorted(VALID_WAIT_UNTIL))}."
        )

    try:
        from playwright.sync_api import sync_playwright

        selectors = _parse_strip_selectors(strip_selectors)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(url, wait_until=wait_until, timeout=timeout_ms)
                snapshot = get_page_html_content(
                    page,
                    root_selector=root_selector,
                    include_form_values=True,
                    include_visible_text=include_visible_text,
                    strip_selectors=selectors,
                    mask_passwords=mask_passwords,
                )
                return {
                    "status": "success",
                    "browser_mode": "local",
                    "headless": headless,
                    "navigated_to": url,
                    **snapshot,
                }
            finally:
                browser.close()
    except Exception as exc:
        return _error_response(str(exc))
