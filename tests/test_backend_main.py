from src.backend import main


class FakeDesensitizer:
    def scan_entities(self, text, entity_types=None):
        assert text == "联系我: 13800001111"
        assert entity_types == ["Phone"]
        return [
            {"type": "Phone", "value": "13800001111"},
            {"type": "Phone", "value": "13800001111"},
        ]


def test_json_safe_decodes_nested_bytes():
    payload = {"items": [b"abc", {"value": b"\xe4\xbd\xa0\xe5\xa5\xbd"}]}

    assert main._json_safe(payload) == {"items": ["abc", {"value": "你好"}]}


def test_desensitize_payload_returns_frontend_contract(monkeypatch):
    monkeypatch.setattr(main, "DES", FakeDesensitizer())

    payload = main._desensitize_payload("联系我: 13800001111", entity_types=["Phone"])

    assert payload["original"] == "联系我: 13800001111"
    assert payload["desensitized"] == "联系我: <Phone[1].Mobile>"
    assert payload["entities"] == [{"type": "Phone", "value": "13800001111"}]
    assert payload["entity_count"] == 1
