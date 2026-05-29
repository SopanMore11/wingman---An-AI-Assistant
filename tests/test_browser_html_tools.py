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
