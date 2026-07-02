from src.tools.browser_html_tools import get_page_html_content


class FakePage:
    def __init__(self, response):
        self.response = response
        self.last_script = None
        self.last_arg = None

    def evaluate(self, script, arg):
        self.last_script = script
        self.last_arg = arg
        return dict(self.response)


def test_get_page_html_content_adds_content_length_and_defaults():
    page = FakePage(
        {
            "url": "https://example.com",
            "title": "Example",
            "root_selector": "body",
            "html": "<body><button>Apply</button></body>",
            "visible_text": None,
        }
    )

    result = get_page_html_content(page)

    assert result["content_length"] == len(result["html"])
    assert page.last_arg["rootSelector"] == "body"
    assert page.last_arg["includeFormValues"] is True
    assert page.last_arg["includeVisibleText"] is False
    assert "script" in page.last_arg["stripSelectors"]


def test_get_page_html_content_respects_overrides():
    page = FakePage(
        {
            "url": "https://example.com/form",
            "title": "Form",
            "root_selector": "#app",
            "html": "<div id='app'><input value='alice'></div>",
            "visible_text": "Name",
        }
    )

    result = get_page_html_content(
        page,
        root_selector="#app",
        include_form_values=False,
        include_visible_text=True,
        strip_selectors=["script", ".ads"],
        mask_passwords=False,
    )

    assert result["root_selector"] == "#app"
    assert result["visible_text"] == "Name"
    assert page.last_arg["rootSelector"] == "#app"
    assert page.last_arg["includeFormValues"] is False
    assert page.last_arg["includeVisibleText"] is True
    assert page.last_arg["stripSelectors"] == ["script", ".ads"]
    assert page.last_arg["maskPasswords"] is False


def test_get_page_html_content_truncates_large_html():
    long_html = "<body>" + "x" * 500 + "</body>"
    page = FakePage(
        {
            "url": "https://example.com",
            "title": "Big",
            "root_selector": "body",
            "html": long_html,
            "visible_text": None,
        }
    )

    result = get_page_html_content(page, max_html_length=50)

    assert result["content_length"] == len(long_html)
    assert len(result["html"]) == 50
    assert result["truncated"] is True


def test_get_page_html_content_no_truncation_when_under_limit():
    short_html = "<body>hi</body>"
    page = FakePage(
        {
            "url": "https://example.com",
            "title": "Small",
            "root_selector": "body",
            "html": short_html,
            "visible_text": None,
        }
    )

    result = get_page_html_content(page, max_html_length=1000)

    assert result["content_length"] == len(short_html)
    assert result["html"] == short_html
    assert result["truncated"] is False


def test_get_page_html_content_no_limit_when_none():
    long_html = "x" * 500_000
    page = FakePage(
        {
            "url": "https://example.com",
            "title": "Huge",
            "root_selector": "body",
            "html": long_html,
            "visible_text": None,
        }
    )

    result = get_page_html_content(page, max_html_length=None)

    assert len(result["html"]) == 500_000
    assert result["truncated"] is False
