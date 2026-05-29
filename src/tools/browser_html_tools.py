from __future__ import annotations

from typing import Any

DEFAULT_STRIP_SELECTORS = [
    "script",
    "style",
    "noscript",
    "svg defs",
    "template",
]


def get_page_html_content(
    page: Any,
    *,
    root_selector: str | None = "body",
    include_form_values: bool = True,
    include_visible_text: bool = False,
    strip_selectors: list[str] | None = None,
    mask_passwords: bool = True,
) -> dict[str, Any]:
    """
    Capture a cleaned HTML snapshot from a Playwright page.

    The returned HTML preserves the current state of inputs, textareas, and
    selects so an external agent can decide what to click or fill next.
    """
    selectors_to_strip = strip_selectors or DEFAULT_STRIP_SELECTORS

    snapshot = page.evaluate(
        """({ rootSelector, stripSelectors, includeFormValues, includeVisibleText, maskPasswords }) => {
            const root = rootSelector ? document.querySelector(rootSelector) : document.documentElement;
            if (!root) {
                throw new Error(`Root selector not found: ${rootSelector}`);
            }

            const clone = root.cloneNode(true);

            const removeNoise = (node) => {
                if (!stripSelectors || stripSelectors.length === 0) {
                    return;
                }
                for (const selector of stripSelectors) {
                    for (const element of node.querySelectorAll(selector)) {
                        element.remove();
                    }
                }
            };

            const syncFormState = () => {
                if (!includeFormValues) {
                    return;
                }

                const sourceInputs = Array.from(root.querySelectorAll("input"));
                const cloneInputs = Array.from(clone.querySelectorAll("input"));
                sourceInputs.forEach((source, index) => {
                    const target = cloneInputs[index];
                    if (!target) {
                        return;
                    }

                    const type = (source.getAttribute("type") || "text").toLowerCase();
                    if (type === "checkbox" || type === "radio") {
                        if (source.checked) {
                            target.setAttribute("checked", "checked");
                        } else {
                            target.removeAttribute("checked");
                        }
                    }

                    if (type === "password" && maskPasswords) {
                        target.setAttribute("value", "***");
                    } else if (source.value != null) {
                        target.setAttribute("value", source.value);
                    }
                });

                const sourceTextareas = Array.from(root.querySelectorAll("textarea"));
                const cloneTextareas = Array.from(clone.querySelectorAll("textarea"));
                sourceTextareas.forEach((source, index) => {
                    const target = cloneTextareas[index];
                    if (!target) {
                        return;
                    }
                    target.textContent = source.value || "";
                });

                const sourceSelects = Array.from(root.querySelectorAll("select"));
                const cloneSelects = Array.from(clone.querySelectorAll("select"));
                sourceSelects.forEach((source, index) => {
                    const target = cloneSelects[index];
                    if (!target) {
                        return;
                    }

                    target.setAttribute("value", source.value || "");
                    const sourceOptions = Array.from(source.options);
                    const targetOptions = Array.from(target.options);

                    sourceOptions.forEach((sourceOption, optionIndex) => {
                        const targetOption = targetOptions[optionIndex];
                        if (!targetOption) {
                            return;
                        }

                        if (sourceOption.selected) {
                            targetOption.setAttribute("selected", "selected");
                        } else {
                            targetOption.removeAttribute("selected");
                        }
                    });
                });
            };

            removeNoise(clone);
            syncFormState();

            return {
                url: window.location.href,
                title: document.title,
                root_selector: rootSelector || "documentElement",
                html: clone.outerHTML,
                visible_text: includeVisibleText ? (root.innerText || "") : null,
            };
        }""",
        {
            "rootSelector": root_selector,
            "stripSelectors": selectors_to_strip,
            "includeFormValues": include_form_values,
            "includeVisibleText": include_visible_text,
            "maskPasswords": mask_passwords,
        },
    )

    snapshot["content_length"] = len(snapshot["html"])
    return snapshot


def get_page_html_via_cdp(
    *,
    cdp_url: str = "http://127.0.0.1:9222",
    page_index: int = 0,
    root_selector: str | None = "body",
    include_form_values: bool = True,
    include_visible_text: bool = False,
    strip_selectors: list[str] | None = None,
    mask_passwords: bool = True,
) -> dict[str, Any]:
    """Connect to an existing Chromium session over CDP and capture HTML."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        try:
            if browser.contexts:
                context = browser.contexts[0]
            else:
                context = browser.new_context()

            if len(context.pages) > page_index:
                page = context.pages[page_index]
                created_page = False
            else:
                page = context.new_page()
                created_page = True

            try:
                return get_page_html_content(
                    page,
                    root_selector=root_selector,
                    include_form_values=include_form_values,
                    include_visible_text=include_visible_text,
                    strip_selectors=strip_selectors,
                    mask_passwords=mask_passwords,
                )
            finally:
                if created_page:
                    page.close()
        finally:
            browser.close()
