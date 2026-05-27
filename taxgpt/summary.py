from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from .finanzonline import category_display_label, kennzahl_for_category
from .models import TaxEntry, TaxYear
from .taxonomy import GROUP_LABELS, get_category


def build_finanzonline_summary(tax_year: TaxYear) -> dict[str, Any]:
    section_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    grouped_entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    group_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for entry in tax_year.entries:
        category = get_category(entry.category)
        deductible_amount = entry.deductible_amount.quantize(Decimal("0.01"))
        section_totals[category.finanzonline_section] += deductible_amount
        group_totals[category.group] += deductible_amount
        grouped_entries[category.finanzonline_section].append(_entry_row(entry, deductible_amount))

    return {
        "year": tax_year.year,
        "filing_kind": tax_year.filing_kind,
        "facts": tax_year.facts,
        "sections": [
            {
                "name": section,
                "total": total.quantize(Decimal("0.01")),
                "entries": grouped_entries[section],
            }
            for section, total in sorted(section_totals.items())
        ],
        "group_totals": [
            {
                "group": group,
                "label": GROUP_LABELS.get(group, group.title()),
                "total": total.quantize(Decimal("0.01")),
            }
            for group, total in sorted(group_totals.items())
        ],
        "total_deductions": sum(
            (
                total
                for group, total in group_totals.items()
                if group in {"work_expense", "special_expense", "extraordinary"}
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01")),
        "total_income": group_totals.get("income", Decimal("0.00")).quantize(Decimal("0.01")),
    }


def _entry_row(entry: TaxEntry, deductible_amount: Decimal) -> dict[str, Any]:
    category = get_category(entry.category)
    return {
        "id": entry.id,
        "category": category_display_label(entry.category, category.label),
        "kennzahl": kennzahl_for_category(entry.category),
        "hint": category.hint,
        "amount": entry.amount.quantize(Decimal("0.01")),
        "deductible_percent": entry.deductible_percent,
        "deductible_amount": deductible_amount,
        "paid_on": entry.paid_on,
        "vendor": entry.vendor,
        "description": entry.description,
        "source": entry.document.original_filename if entry.document else "Manuell",
    }
