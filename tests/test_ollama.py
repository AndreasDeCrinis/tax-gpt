from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from taxgpt.services.ollama import OllamaError, analyze_document


class FakeResponse:
    def __init__(self, *, status_code: int, payload: dict, url: str = "http://ollama/api/generate"):
        self.status_code = status_code
        self.payload = payload
        self.url = url
        self.text = json.dumps(payload)
        self.ok = 200 <= status_code < 400
        self.request = SimpleNamespace(method="POST")

    def json(self):
        return self.payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(self.text)


def test_missing_ollama_model_error_lists_available_models(tmp_path, monkeypatch):
    document = tmp_path / "invoice.txt"
    document.write_text("Steuerberatung 180 EUR", encoding="utf-8")

    def fake_post(*args, **kwargs):
        return FakeResponse(status_code=404, payload={"error": "model 'llama3.2' not found"})

    def fake_get(*args, **kwargs):
        return FakeResponse(
            status_code=200,
            payload={"models": [{"name": "llama3.1:latest"}, {"name": "qwen3:8b"}]},
            url="http://ollama/api/tags",
        )

    monkeypatch.setattr("taxgpt.services.ollama.requests.post", fake_post)
    monkeypatch.setattr("taxgpt.services.ollama.requests.get", fake_get)

    with pytest.raises(OllamaError) as error:
        analyze_document(
            path=str(document),
            original_filename="invoice.txt",
            mime_type="text/plain",
            base_url="http://ollama",
            model="llama3.2",
            timeout=90,
        )

    message = str(error.value)
    assert "model 'llama3.2' not found" in message
    assert "llama3.1:latest" in message
    assert "OLLAMA_MODEL" in message


def test_image_document_uses_vision_model(tmp_path, monkeypatch):
    document = tmp_path / "invoice.png"
    document.write_bytes(b"not really a png, enough for base64")
    captured_payload = {}

    def fake_post(*args, **kwargs):
        captured_payload.update(kwargs["json"])
        return FakeResponse(
            status_code=200,
            payload={
                "response": json.dumps(
                    {
                        "category": "tax_advice",
                        "amount": "180",
                        "vendor": "Steuerhilfe",
                        "date": "2026-01-05",
                        "description": "Steuerberatung",
                        "confidence": 0.8,
                    }
                )
            },
        )

    monkeypatch.setattr("taxgpt.services.ollama.requests.post", fake_post)

    result = analyze_document(
        path=str(document),
        original_filename="invoice.png",
        mime_type="image/png",
        base_url="http://ollama",
        model="llama3.1:latest",
        vision_model="minicpm-v:latest",
        timeout=90,
    )

    assert captured_payload["model"] == "minicpm-v:latest"
    assert captured_payload["images"]
    assert result["category"] == "tax_advice"


def test_document_analysis_normalises_invoice_total_and_line_items(tmp_path, monkeypatch):
    document = tmp_path / "invoice.txt"
    document.write_text("Monitor 120 EUR\nPrivate item 180 EUR\nTotal 300 EUR", encoding="utf-8")

    def fake_post(*args, **kwargs):
        return FakeResponse(
            status_code=200,
            payload={
                "response": json.dumps(
                    {
                        "category": "computer",
                        "invoice_total": "300.00",
                        "vendor": "Electronics Shop",
                        "date": "2025-04-02",
                        "description": "Mixed invoice",
                        "confidence": 0.9,
                        "line_items": [
                            {
                                "description": "Monitor",
                                "amount": "120.00",
                                "category": "computer",
                                "tax_relevant": True,
                                "deductible_percent": 50,
                                "reasoning": "Work display",
                            },
                            {
                                "description": "Private item",
                                "amount": "180.00",
                                "category": "",
                                "tax_relevant": False,
                                "deductible_percent": 100,
                            },
                        ],
                    }
                )
            },
        )

    monkeypatch.setattr("taxgpt.services.ollama.requests.post", fake_post)

    result = analyze_document(
        path=str(document),
        original_filename="invoice.txt",
        mime_type="text/plain",
        base_url="http://ollama",
        model="llama3.1:latest",
        timeout=90,
    )

    assert result["invoice_total"] == Decimal("300.00")
    assert result["amount"] == Decimal("60.00")
    assert result["line_items"][0]["category"] == "computer"
    assert result["line_items"][0]["tax_relevant"] is True
    assert result["line_items"][1]["tax_relevant"] is False
