from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

from taxgpt.models import Document, TaxEntry, TaxYear, User, db
from taxgpt.summary import build_finanzonline_summary

from .conftest import register_and_login


def test_register_creates_default_2025_year(client, app):
    response = register_and_login(client)

    assert response.status_code == 200
    assert b"2025" in response.data

    with app.app_context():
        user = User.query.filter_by(email="ada@example.com").one()
        assert [year.year for year in user.tax_years] == [2025]


def test_create_2026_year_and_add_manual_entry(client, app):
    register_and_login(client)
    client.post("/years", data={"year": "2026"}, follow_redirects=True)

    with app.app_context():
        tax_year = TaxYear.query.filter_by(year=2026).one()

    response = client.post(
        f"/years/{tax_year.id}/entries",
        data={
            "category": "computer",
            "amount": "1200",
            "deductible_percent": "60",
            "paid_on": "2026-02-14",
            "vendor": "Laptop Shop",
            "description": "Work laptop",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Work laptop" in response.data

    with app.app_context():
        entry = TaxEntry.query.one()
        assert entry.deductible_amount == Decimal("720.00")


def test_added_entries_roll_up_to_correct_finanzonline_kennzahl(client, app):
    register_and_login(client)
    with app.app_context():
        tax_year = TaxYear.query.filter_by(year=2025).one()
        tax_year_id = tax_year.id

    client.post(
        f"/years/{tax_year_id}/entries",
        data={
            "category": "computer",
            "amount": "1200",
            "deductible_percent": "60",
            "description": "Laptop beruflicher Anteil",
        },
        follow_redirects=True,
    )
    client.post(
        f"/years/{tax_year_id}/entries",
        data={
            "category": "family_home_trips",
            "amount": "300",
            "deductible_percent": "100",
            "description": "Familienheimfahrten",
        },
        follow_redirects=True,
    )
    client.post(
        f"/years/{tax_year_id}/entries",
        data={
            "category": "double_household",
            "amount": "500",
            "deductible_percent": "50",
            "description": "Doppelte Haushaltsführung",
        },
        follow_redirects=True,
    )

    response = client.get(f"/years/{tax_year_id}/summary")

    assert b"169" in response.data
    assert b"720.00" in response.data
    assert b"300" in response.data
    assert b"300.00" in response.data
    assert b"723" in response.data
    assert b"250.00" in response.data


def test_existing_entry_can_be_modified_to_another_kennzahl(client, app):
    register_and_login(client)
    with app.app_context():
        tax_year = TaxYear.query.filter_by(year=2025).one()
        tax_year_id = tax_year.id

    client.post(
        f"/years/{tax_year_id}/entries",
        data={
            "category": "computer",
            "amount": "1000",
            "deductible_percent": "100",
            "description": "Computer",
        },
        follow_redirects=True,
    )

    with app.app_context():
        entry_id = TaxEntry.query.one().id

    client.post(
        f"/entries/{entry_id}",
        data={
            "category": "training",
            "amount": "500",
            "deductible_percent": "50",
            "description": "Kurs",
        },
        follow_redirects=True,
    )

    response = client.get(f"/years/{tax_year_id}/summary")

    assert b"722" in response.data
    assert b"250.00" in response.data
    assert b"1000.00" not in response.data

    with app.app_context():
        entry = db.session.get(TaxEntry, entry_id)
        assert entry.category == "training"
        assert entry.deductible_amount == Decimal("250.00")


def test_checklist_adds_only_filled_items(client, app):
    register_and_login(client)
    with app.app_context():
        tax_year = TaxYear.query.filter_by(year=2025).one()
        tax_year_id = tax_year.id

    response = client.post(
        f"/years/{tax_year_id}/checklist",
        data={
            "amount_training": "350.50",
            "deductible_training": "100",
            "vendor_training": "Course GmbH",
            "description_training": "Python course",
            "amount_medical_costs": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        entries = TaxEntry.query.all()
        assert len(entries) == 1
        assert entries[0].category == "training"


def test_finanzonline_fields_are_saved_grouped_and_preserved(client, app):
    register_and_login(client)
    with app.app_context():
        tax_year = TaxYear.query.filter_by(year=2025).one()
        tax_year_id = tax_year.id

    dashboard = client.get(f"/years/{tax_year_id}")
    assert "Kennzahl 169".encode() in dashboard.data
    assert "Pendlerpauschale / Pendlereuro".encode() in dashboard.data
    assert b'name="fo_169"' in dashboard.data
    assert b"readonly" in dashboard.data

    response = client.post(
        f"/years/{tax_year_id}/finanzonline",
        data={
            "fo_718": "1234.00",
            "fo_916": "91.60",
            "fo_occupation": "Technischer Angestellter",
            "fo_169": "839.41",
            "fo_722": "774.12",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "FinanzOnline-Kennzahlen gespeichert.".encode() in response.data

    summary = client.get(f"/years/{tax_year_id}/summary")
    assert b"839.41" not in summary.data
    assert "Technischer Angestellter".encode() in summary.data

    client.post(
        f"/years/{tax_year_id}/settings",
        data={"filing_kind": "arbeitnehmerveranlagung", "tax_number": "12 345/6789"},
        follow_redirects=True,
    )

    with app.app_context():
        facts = db.session.get(TaxYear, tax_year_id).facts
        assert facts["tax_number"] == "12 345/6789"
        assert facts["finanzonline_fields"]["fo_occupation"] == "Technischer Angestellter"
        assert "fo_169" not in facts["finanzonline_fields"]


def test_summary_groups_entries_by_finanzonline_section(app):
    with app.app_context():
        user = User(email="ada@example.com", display_name="Ada")
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()
        tax_year = TaxYear(user_id=user.id, year=2025)
        db.session.add(tax_year)
        db.session.flush()
        db.session.add(
            TaxEntry(
                tax_year_id=tax_year.id,
                group="work_expense",
                category="internet_phone",
                label="Internet and phone",
                amount=Decimal("100.00"),
                deductible_percent=Decimal("50.00"),
            )
        )
        db.session.add(
            TaxEntry(
                tax_year_id=tax_year.id,
                group="special_expense",
                category="tax_advice",
                label="Tax advice",
                amount=Decimal("200.00"),
                deductible_percent=Decimal("100.00"),
            )
        )
        db.session.commit()

        summary = build_finanzonline_summary(tax_year)

    assert summary["total_deductions"] == Decimal("250.00")
    assert {section["name"] for section in summary["sections"]} == {"Sonderausgaben", "Werbungskosten"}


def test_upload_document_analysis_can_be_applied(client, app, monkeypatch):
    register_and_login(client)
    with app.app_context():
        tax_year = TaxYear.query.filter_by(year=2025).one()
        tax_year_id = tax_year.id

    def fake_analyze_document(**kwargs):
        return {
            "category": "tax_advice",
            "amount": Decimal("180.00"),
            "vendor": "Tax Helper",
            "date": date(2025, 3, 1),
            "description": "Tax return preparation",
            "confidence": 0.95,
            "extracted_text": "Tax Helper 180 EUR",
        }

    monkeypatch.setattr("taxgpt.views.analyze_document", fake_analyze_document)

    response = client.post(
        f"/years/{tax_year_id}/documents",
        data={
            "analyze": "on",
            "document": (io.BytesIO(b"invoice text"), "invoice.txt"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        document = Document.query.one()
        assert document.status == "analysed"
        document_id = document.id

    client.post(f"/documents/{document_id}/apply", follow_redirects=True)

    with app.app_context():
        entry = TaxEntry.query.one()
        assert entry.category == "tax_advice"
        assert entry.amount == Decimal("180.00")
