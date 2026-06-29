import pytest

from src.core import desensitizer as d


def test_sanitize_user_text_basic():
    s = "Hello [USER_TEXT] /USER_TEXT [SYSTEM]"
    out = d._sanitize_user_text(s)
    assert isinstance(out, str)
    # basic sanity: output should still contain "Hello" and not raise
    assert "Hello" in out


def test_parse_entries_empty_and_list():
    # empty list JSON
    out = d._parse_entries("[]")
    assert isinstance(out, list)
    assert out == []

    # JSON array with entries
    raw = '[{"type": "Phone", "value": "13800001111"}]'
    out2 = d._parse_entries(raw)
    assert isinstance(out2, list)
    assert len(out2) == 1
    assert out2[0].get("type") == "Phone"
    assert out2[0].get("value") == "13800001111"


def test_deduplicate_entries():
    entries = [
        {"type": "Phone", "value": "13800001111"},
        {"type": "Phone", "value": "13800001111"},
    ]
    res = d._deduplicate_entries(entries)
    assert isinstance(res, list)
    # duplicates should be removed
    assert len(res) == 1


def test_replace_with_tags_simple():
    text = "联系我: 13800001111 或 alice@example.com"
    entries = [
        {"type": "Phone", "value": "13800001111", "tag": "[PHONE]"},
        {"type": "Email", "value": "alice@example.com", "tag": "[EMAIL]"},
    ]
    out = d.replace_with_tags(text, entries)
    assert isinstance(out, str)
    # original sensitive values should not appear verbatim
    assert "13800001111" not in out
    assert "alice@example.com" not in out
    # tags should be present
    assert "[PHONE]" in out
    assert "[EMAIL]" in out
