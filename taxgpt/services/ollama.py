from __future__ import annotations

import base64
import json
import mimetypes
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import requests
from pypdf import PdfReader

from taxgpt.taxonomy import CATEGORIES


class OllamaError(RuntimeError):
    pass


def extract_document_text(path: str, mime_type: str = "") -> str:
    file_path = Path(path)
    guessed_type = mime_type or mimetypes.guess_type(file_path.name)[0] or ""

    if guessed_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if guessed_type.startswith("text/") or file_path.suffix.lower() in {".txt", ".csv", ".md"}:
        return file_path.read_text(encoding="utf-8", errors="replace").strip()

    return ""


def analyze_document(
    *,
    path: str,
    original_filename: str,
    mime_type: str,
    base_url: str,
    model: str,
    vision_model: str | None = None,
    timeout: int,
) -> dict[str, Any]:
    text = extract_document_text(path, mime_type)
    prompt = _build_prompt(original_filename=original_filename, extracted_text=text)
    selected_model = model
    payload: dict[str, Any] = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    if not text and _looks_like_image(mime_type, path):
        selected_model = vision_model or model
        payload["model"] = selected_model
        payload["images"] = [_base64_file(path)]

    response = requests.post(f"{base_url.rstrip('/')}/api/generate", json=payload, timeout=timeout)
    _raise_for_ollama_error(response, base_url=base_url, timeout=timeout)
    body = response.json()
    raw_response = body.get("response", "")
    parsed = _parse_json(raw_response)
    parsed["raw_response"] = raw_response
    parsed["extracted_text"] = text
    parsed["category"] = _normalise_category(parsed.get("category", ""))
    parsed["invoice_total"] = _decimal_or_none(parsed.get("invoice_total"))
    parsed["amount"] = _decimal_or_none(parsed.get("amount"))
    parsed["date"] = _date_or_none(parsed.get("date"))
    parsed["confidence"] = _confidence(parsed.get("confidence"))
    parsed["line_items"] = _normalise_line_items(parsed.get("line_items"))
    if parsed["amount"] is None:
        parsed["amount"] = _selected_line_total(parsed["line_items"])
    return parsed


def _raise_for_ollama_error(response: requests.Response, *, base_url: str, timeout: int) -> None:
    if response.ok:
        return

    error_text = _response_error_text(response)
    message = f"Ollama returned HTTP {response.status_code} for POST {response.url}: {error_text}"
    available_models = _available_models(base_url, timeout)
    if available_models:
        message += f" Installierte Modelle: {', '.join(available_models)}."
    if response.status_code == 404 and "model" in error_text.lower():
        message += " Bitte OLLAMA_MODEL oder OLLAMA_VISION_MODEL auf ein installiertes Modell setzen oder das Modell mit `ollama pull <modell>` installieren."
    raise OllamaError(message)


def _response_error_text(response: requests.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text.strip() or "Keine Fehlermeldung im Response-Body."

    if isinstance(data, dict):
        return str(data.get("error") or data)
    return str(data)


def _available_models(base_url: str, timeout: int) -> list[str]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=min(timeout, 10))
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    models = data.get("models", []) if isinstance(data, dict) else []
    names = []
    for model in models:
        if isinstance(model, dict) and model.get("name"):
            names.append(str(model["name"]))
    return names


def _build_prompt(*, original_filename: str, extracted_text: str) -> str:
    category_lines = "\n".join(f"- {item.code}: {item.label} ({item.finanzonline_section})" for item in CATEGORIES)
    document_text = extracted_text[:12000] if extracted_text else "No text was extracted. If an image is attached, read it visually."
    return f"""
You classify Austrian income-tax documents for a private tax preparation tool.

Choose exactly one category code from this list:
{category_lines}

Return only JSON with these keys:
category, invoice_total, amount, vendor, date, description, confidence, reasoning, line_items.

Rules:
- invoice_total must be the full gross invoice total if visible, otherwise null.
- line_items must be a list of all invoice positions you can identify. Each item must have:
  description, amount, category, tax_relevant, deductible_percent, reasoning.
- For line item amount, use the gross amount of that invoice position if visible.
- For category inside line_items, choose exactly one category code from the list above, or null if unclear.
- tax_relevant should be true only if the item is plausibly deductible for an Austrian income tax return.
- Mark mixed/private items as false when the job connection is unclear, so the user can decide manually.
- amount must be the sum of line_items that are tax_relevant=true, adjusted by deductible_percent. If there are no line_items, use the gross tax-relevant amount paid by the taxpayer if visible, otherwise null.
- date must be ISO format YYYY-MM-DD if visible, otherwise null.
- confidence is a number from 0 to 1.
- description should be short and suitable for a tax entry.
- If it is not tax relevant, use category "other_work_expense" only if there is a plausible work link; otherwise use "extraordinary_other" with low confidence.

Filename: {original_filename}
Document text:
{document_text}
""".strip()


def _parse_json(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {"description": raw[:500], "confidence": 0}


def _normalise_category(category: str) -> str:
    allowed = {item.code for item in CATEGORIES}
    return category if category in allowed else ""


def _normalise_line_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    line_items = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue

        amount = _decimal_or_none(item.get("amount"))
        line_items.append(
            {
                "id": str(item.get("id") or index),
                "description": str(item.get("description") or item.get("name") or f"Position {index}")[:500],
                "amount": amount,
                "category": _normalise_category(str(item.get("category") or "")),
                "tax_relevant": _bool_value(item.get("tax_relevant")),
                "deductible_percent": _percent_or_default(item.get("deductible_percent")),
                "reasoning": str(item.get("reasoning") or "")[:1000],
            }
        )
    return line_items


def _selected_line_total(line_items: list[dict[str, Any]]) -> Decimal | None:
    total = Decimal("0.00")
    found = False
    for item in line_items:
        amount = item.get("amount")
        if item.get("tax_relevant") and amount is not None:
            total += amount * item["deductible_percent"] / Decimal("100")
            found = True
    return total.quantize(Decimal("0.01")) if found else None


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ja", "y"}
    return bool(value)


def _percent_or_default(value: Any) -> Decimal:
    percentage = _decimal_or_none(value)
    if percentage is None:
        return Decimal("100.00")
    return max(Decimal("0.00"), min(Decimal("100.00"), percentage))


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in {None, ""}:
        return None
    try:
        return Decimal(str(value).replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _date_or_none(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _looks_like_image(mime_type: str, path: str) -> bool:
    return mime_type.startswith("image/") or Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}


def _base64_file(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")
