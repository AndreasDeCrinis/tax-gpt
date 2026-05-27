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
    timeout: int,
) -> dict[str, Any]:
    text = extract_document_text(path, mime_type)
    prompt = _build_prompt(original_filename=original_filename, extracted_text=text)
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    if not text and _looks_like_image(mime_type, path):
        payload["images"] = [_base64_file(path)]

    response = requests.post(f"{base_url.rstrip('/')}/api/generate", json=payload, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    raw_response = body.get("response", "")
    parsed = _parse_json(raw_response)
    parsed["raw_response"] = raw_response
    parsed["extracted_text"] = text
    parsed["category"] = _normalise_category(parsed.get("category", ""))
    parsed["amount"] = _decimal_or_none(parsed.get("amount"))
    parsed["date"] = _date_or_none(parsed.get("date"))
    parsed["confidence"] = _confidence(parsed.get("confidence"))
    return parsed


def _build_prompt(*, original_filename: str, extracted_text: str) -> str:
    category_lines = "\n".join(f"- {item.code}: {item.label} ({item.finanzonline_section})" for item in CATEGORIES)
    document_text = extracted_text[:12000] if extracted_text else "No text was extracted. If an image is attached, read it visually."
    return f"""
You classify Austrian income-tax documents for a private tax preparation tool.

Choose exactly one category code from this list:
{category_lines}

Return only JSON with these keys:
category, amount, vendor, date, description, confidence, reasoning.

Rules:
- amount must be the gross amount paid by the taxpayer if visible, otherwise null.
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
