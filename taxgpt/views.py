from __future__ import annotations

import csv
import io
import json
import secrets
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .finanzonline import (
    FINANZONLINE_FIELD_BY_KEY,
    FINANZONLINE_SECTIONS,
    build_finanzonline_entry_totals,
    build_finanzonline_transfer_values,
    build_finanzonline_value_sources,
    category_display_label,
    finanzonline_values,
    format_money,
    kennzahl_for_category,
    normalise_money,
)
from .models import Document, TaxEntry, TaxYear, User, db
from .services.ollama import analyze_document
from .summary import build_finanzonline_summary
from .taxonomy import CATEGORY_BY_CODE, GROUP_LABELS, categories_for_select, deduction_questions, get_category

bp = Blueprint("web", __name__)

FACT_FIELDS = (
    {"name": "tax_number", "label": "Steuernummer", "type": "text"},
    {"name": "resident_full_year", "label": "Ganzjähriger Wohnsitz in Österreich", "type": "checkbox"},
    {"name": "employer_count", "label": "Anzahl Arbeitgeber/Lohnzettel", "type": "number"},
    {"name": "austrian_employment_income", "label": "Einkünfte aus nichtselbständiger Arbeit in Österreich", "type": "money"},
    {"name": "wage_tax_withheld", "label": "Einbehaltene Lohnsteuer", "type": "money"},
    {"name": "partner_income", "label": "Einkünfte Partnerin/Partner", "type": "money"},
    {"name": "children_count", "label": "Steuerlich relevante Kinder", "type": "number"},
    {"name": "family_bonus_children", "label": "Kinder für den Familienbonus Plus", "type": "number"},
    {"name": "single_earner", "label": "Alleinverdienerabsetzbetrag könnte zustehen", "type": "checkbox"},
    {"name": "single_parent", "label": "Alleinerzieherabsetzbetrag könnte zustehen", "type": "checkbox"},
    {"name": "foreign_income_present", "label": "Auslandseinkünfte oder grenzüberschreitende Angaben", "type": "checkbox"},
    {"name": "self_employed_income_present", "label": "Selbständige oder betriebliche Einkünfte", "type": "checkbox"},
    {"name": "rental_income_present", "label": "Einkünfte aus Vermietung", "type": "checkbox"},
    {"name": "disability_degree", "label": "Grad der Behinderung", "type": "number"},
    {"name": "care_allowance_months", "label": "Monate mit Pflegegeld", "type": "number"},
)

FACT_LABELS = {field["name"]: field["label"] for field in FACT_FIELDS}

DOCUMENT_STATUS_LABELS = {
    "uploaded": "Hochgeladen",
    "analysing": "Analyse läuft",
    "analysed": "Analysiert",
    "analysis_failed": "Analyse fehlgeschlagen",
}

CATEGORY_LABELS = {code: category.label for code, category in CATEGORY_BY_CODE.items()}
CATEGORY_DISPLAY_LABELS = {
    code: category_display_label(code, category.label) for code, category in CATEGORY_BY_CODE.items()
}
CATEGORY_KENNZAHL_LABELS = {code: kennzahl_for_category(code) for code in CATEGORY_BY_CODE}


@bp.before_app_request
def load_current_user() -> None:
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

    if (
        current_app.config.get("ENABLE_CSRF", True)
        and request.method == "POST"
        and request.form.get("csrf_token") != session.get("csrf_token")
    ):
        abort(400, "Invalid CSRF token")


@bp.app_context_processor
def inject_globals() -> dict[str, Any]:
    return {
        "current_user": g.get("user"),
        "csrf_token": session.get("csrf_token", ""),
        "group_labels": GROUP_LABELS,
        "document_status_labels": DOCUMENT_STATUS_LABELS,
        "fact_labels": FACT_LABELS,
        "category_labels": CATEGORY_LABELS,
        "category_display_labels": CATEGORY_DISPLAY_LABELS,
        "category_kennzahl_labels": CATEGORY_KENNZAHL_LABELS,
    }


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(**kwargs: Any) -> Any:
        if g.user is None:
            return redirect(url_for("web.login", next=request.path))
        return view(**kwargs)

    return wrapped


@bp.get("/")
def index() -> str | Response:
    if g.user is None:
        return redirect(url_for("web.login"))
    tax_year = TaxYear.query.filter_by(user_id=g.user.id).order_by(TaxYear.year.desc()).first()
    if tax_year is None:
        tax_year = TaxYear(user_id=g.user.id, year=2025)
        db.session.add(tax_year)
        db.session.commit()
    return redirect(url_for("web.year_dashboard", tax_year_id=tax_year.id))


@bp.route("/register", methods=["GET", "POST"])
def register() -> str | Response:
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        display_name = request.form.get("display_name", "").strip() or email.split("@")[0]
        password = request.form.get("password", "")
        if not email or len(password) < 8:
            flash("Bitte E-Mail und ein Passwort mit mindestens 8 Zeichen verwenden.", "error")
            return render_template("auth/register.html")

        user = User(email=email, display_name=display_name)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Diese E-Mail-Adresse ist bereits registriert.", "error")
            return render_template("auth/register.html")

        session["user_id"] = user.id
        flash("Konto erstellt.", "success")
        return redirect(url_for("web.index"))

    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login() -> str | Response:
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash("E-Mail oder Passwort ist falsch.", "error")
            return render_template("auth/login.html")
        session["user_id"] = user.id
        flash("Angemeldet.", "success")
        return redirect(request.args.get("next") or url_for("web.index"))
    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout() -> Response:
    session.clear()
    return redirect(url_for("web.login"))


@bp.post("/years")
@login_required
def create_year() -> Response:
    year = _int_form("year", 2025)
    if year < 2025:
        flash("Das erste unterstützte Steuerjahr ist 2025.", "error")
        return redirect(url_for("web.index"))
    existing = TaxYear.query.filter_by(user_id=g.user.id, year=year).first()
    if existing:
        return redirect(url_for("web.year_dashboard", tax_year_id=existing.id))
    tax_year = TaxYear(user_id=g.user.id, year=year)
    db.session.add(tax_year)
    db.session.commit()
    return redirect(url_for("web.year_dashboard", tax_year_id=tax_year.id))


@bp.get("/years/<int:tax_year_id>")
@login_required
def year_dashboard(tax_year_id: int) -> str:
    tax_year = _owned_tax_year(tax_year_id)
    summary = build_finanzonline_summary(tax_year)
    return render_template(
        "dashboard.html",
        tax_year=tax_year,
        tax_years=g.user.tax_years,
        categories=categories_for_select(),
        questions=deduction_questions(),
        fact_fields=FACT_FIELDS,
        finanzonline_sections=FINANZONLINE_SECTIONS,
        finanzonline_values=finanzonline_values(tax_year),
        finanzonline_entry_totals=build_finanzonline_entry_totals(tax_year),
        finanzonline_transfer_values=build_finanzonline_transfer_values(tax_year),
        finanzonline_value_sources=build_finanzonline_value_sources(tax_year),
        summary=summary,
    )


@bp.post("/years/<int:tax_year_id>/settings")
@login_required
def update_settings(tax_year_id: int) -> Response:
    tax_year = _owned_tax_year(tax_year_id)
    facts = tax_year.facts
    for field in FACT_FIELDS:
        name = field["name"]
        if field["type"] == "checkbox":
            facts[name] = name in request.form
        elif field["type"] in {"money", "number"}:
            facts[name] = request.form.get(name, "").strip()
        else:
            facts[name] = request.form.get(name, "").strip()
    tax_year.filing_kind = request.form.get("filing_kind", tax_year.filing_kind)
    tax_year.notes = request.form.get("notes", "").strip()
    tax_year.set_facts(facts)
    db.session.commit()
    flash("Allgemeine Daten gespeichert.", "success")
    return _dashboard_redirect(tax_year.id, "allgemeine-daten")


@bp.post("/years/<int:tax_year_id>/finanzonline")
@login_required
def update_finanzonline_fields(tax_year_id: int) -> Response:
    tax_year = _owned_tax_year(tax_year_id)
    entry_totals = build_finanzonline_entry_totals(tax_year)
    values: dict[str, str] = {}
    for key, field in FINANZONLINE_FIELD_BY_KEY.items():
        if field.input_type == "money" and field.linked_categories:
            continue
        value = request.form.get(key, "").strip()
        if not value:
            continue
        if field.input_type == "money":
            normalised_value = normalise_money(value)
            if key in entry_totals and normalised_value == format_money(entry_totals[key]):
                continue
            values[key] = normalised_value
        else:
            values[key] = value

    facts = tax_year.facts
    facts["finanzonline_fields"] = values
    tax_year.set_facts(facts)
    db.session.commit()
    flash("FinanzOnline-Kennzahlen gespeichert.", "success")
    return _dashboard_redirect(tax_year.id, "finanzonline-kennzahlen")


@bp.post("/years/<int:tax_year_id>/entries")
@login_required
def add_entry(tax_year_id: int) -> Response:
    tax_year = _owned_tax_year(tax_year_id)
    entry = TaxEntry(tax_year_id=tax_year.id)
    _apply_entry_form(entry)
    db.session.add(entry)
    db.session.commit()
    flash("Eintrag hinzugefügt.", "success")
    return _dashboard_redirect(tax_year.id, "eintraege")


@bp.post("/entries/<int:entry_id>")
@login_required
def update_entry(entry_id: int) -> Response:
    entry = TaxEntry.query.join(TaxYear).filter(TaxEntry.id == entry_id, TaxYear.user_id == g.user.id).first_or_404()
    _apply_entry_form(entry)
    db.session.commit()
    flash("Eintrag aktualisiert.", "success")
    return _dashboard_redirect(entry.tax_year_id, f"entry-{entry.id}")


@bp.post("/years/<int:tax_year_id>/checklist")
@login_required
def save_checklist(tax_year_id: int) -> Response:
    tax_year = _owned_tax_year(tax_year_id)
    created = 0
    for category in deduction_questions():
        amount = _decimal_value(request.form.get(f"amount_{category.code}", ""))
        if amount <= 0:
            continue
        entry = TaxEntry(
            tax_year_id=tax_year.id,
            group=category.group,
            category=category.code,
            label=category.label,
            amount=amount,
            deductible_percent=_decimal_value(
                request.form.get(f"deductible_{category.code}", str(category.default_deductible_percent))
            ),
            vendor=request.form.get(f"vendor_{category.code}", "").strip(),
            description=request.form.get(f"description_{category.code}", "").strip(),
        )
        db.session.add(entry)
        created += 1
    db.session.commit()
    flash(f"{created} Checklisten-Eintrag{'e' if created != 1 else ''} hinzugefügt.", "success")
    return _dashboard_redirect(tax_year.id, "abzugs-checkliste")


@bp.post("/entries/<int:entry_id>/delete")
@login_required
def delete_entry(entry_id: int) -> Response:
    entry = TaxEntry.query.join(TaxYear).filter(TaxEntry.id == entry_id, TaxYear.user_id == g.user.id).first_or_404()
    tax_year_id = entry.tax_year_id
    db.session.delete(entry)
    db.session.commit()
    flash("Eintrag gelöscht.", "success")
    return _dashboard_redirect(tax_year_id, "eintraege")


@bp.post("/years/<int:tax_year_id>/documents")
@login_required
def upload_document(tax_year_id: int) -> Response:
    tax_year = _owned_tax_year(tax_year_id)
    uploaded = request.files.get("document")
    if not uploaded or not uploaded.filename:
        flash("Bitte zuerst ein Dokument auswählen.", "error")
        return _dashboard_redirect(tax_year.id, "dokumente")

    document = _store_document(tax_year, uploaded)
    db.session.add(document)
    db.session.commit()

    if request.form.get("analyze", "on") == "on":
        _analyse_and_update_document(document)
        db.session.commit()

    flash("Dokument hochgeladen.", "success")
    return _dashboard_redirect(tax_year.id, "hochgeladene-dokumente")


@bp.post("/documents/<int:document_id>/analyse")
@login_required
def analyse_existing_document(document_id: int) -> Response:
    document = _owned_document(document_id)
    _analyse_and_update_document(document)
    db.session.commit()
    flash("Dokument analysiert.", "success")
    return _dashboard_redirect(document.tax_year_id, "hochgeladene-dokumente")


@bp.post("/documents/<int:document_id>/apply")
@login_required
def apply_document_suggestion(document_id: int) -> Response:
    document = _owned_document(document_id)
    if not document.suggested_category:
        flash("Es ist kein Kategorie-Vorschlag vorhanden.", "error")
        return _dashboard_redirect(document.tax_year_id, "hochgeladene-dokumente")

    category = get_category(document.suggested_category)
    entry = TaxEntry(
        tax_year_id=document.tax_year_id,
        group=category.group,
        category=category.code,
        label=category.label,
        amount=document.suggested_amount or Decimal("0.00"),
        deductible_percent=Decimal(str(category.default_deductible_percent)),
        paid_on=document.suggested_date,
        vendor=document.suggested_vendor,
        description=document.suggested_description,
        document_id=document.id,
    )
    db.session.add(entry)
    db.session.commit()
    flash("Vorschlag als Steuer-Eintrag übernommen.", "success")
    return _dashboard_redirect(document.tax_year_id, "eintraege")


@bp.get("/years/<int:tax_year_id>/summary")
@login_required
def summary(tax_year_id: int) -> str:
    tax_year = _owned_tax_year(tax_year_id)
    return render_template(
        "summary.html",
        tax_year=tax_year,
        summary=build_finanzonline_summary(tax_year),
        finanzonline_sections=FINANZONLINE_SECTIONS,
        finanzonline_values=finanzonline_values(tax_year),
        finanzonline_entry_totals=build_finanzonline_entry_totals(tax_year),
        finanzonline_transfer_values=build_finanzonline_transfer_values(tax_year),
        finanzonline_value_sources=build_finanzonline_value_sources(tax_year),
    )


@bp.get("/years/<int:tax_year_id>/export.csv")
@login_required
def export_csv(tax_year_id: int) -> Response:
    tax_year = _owned_tax_year(tax_year_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "year",
            "finanzonline_section",
            "category",
            "amount",
            "deductible_percent",
            "deductible_amount",
            "paid_on",
            "vendor",
            "description",
        ]
    )
    transfer_values = build_finanzonline_transfer_values(tax_year)
    value_sources = build_finanzonline_value_sources(tax_year)
    for section in FINANZONLINE_SECTIONS:
        for field in section.fields:
            value = transfer_values.get(field.key, "")
            if not value:
                continue
            writer.writerow(
                [
                    tax_year.year,
                    section.title,
                    f"Kennzahl {field.code}" if field.code else field.label,
                    value,
                    "",
                    "",
                    "",
                    "",
                    f"{field.label} (Quelle: {value_sources.get(field.key, '')})",
                ]
            )
    for entry in tax_year.entries:
        category = get_category(entry.category)
        writer.writerow(
            [
                tax_year.year,
                category.finanzonline_section,
                category.label,
                entry.amount,
                entry.deductible_percent,
                entry.deductible_amount,
                entry.paid_on or "",
                entry.vendor,
                entry.description,
            ]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=taxgpt-{tax_year.year}.csv"},
    )


def _owned_tax_year(tax_year_id: int) -> TaxYear:
    return TaxYear.query.filter_by(id=tax_year_id, user_id=g.user.id).first_or_404()


def _owned_document(document_id: int) -> Document:
    return Document.query.join(TaxYear).filter(Document.id == document_id, TaxYear.user_id == g.user.id).first_or_404()


def _dashboard_redirect(tax_year_id: int, anchor: str) -> Response:
    return redirect(f"{url_for('web.year_dashboard', tax_year_id=tax_year_id)}#{anchor}")


def _apply_entry_form(entry: TaxEntry) -> None:
    category = get_category(request.form.get("category", ""))
    entry.group = category.group
    entry.category = category.code
    entry.label = category.label
    entry.amount = _decimal_form("amount")
    entry.deductible_percent = _decimal_form(
        "deductible_percent", Decimal(str(category.default_deductible_percent))
    )
    entry.paid_on = _date_form("paid_on")
    entry.vendor = request.form.get("vendor", "").strip()
    entry.description = request.form.get("description", "").strip()


def _store_document(tax_year: TaxYear, uploaded: FileStorage) -> Document:
    original = secure_filename(uploaded.filename or "document")
    suffix = Path(original).suffix.lower()
    stored = f"{uuid.uuid4().hex}{suffix}"
    directory = Path(current_app.config["UPLOAD_FOLDER"]) / str(g.user.id) / str(tax_year.year)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / stored
    uploaded.save(path)
    return Document(
        tax_year_id=tax_year.id,
        original_filename=original,
        stored_filename=stored,
        path=str(path),
        mime_type=uploaded.mimetype or "",
        size_bytes=path.stat().st_size,
    )


def _analyse_and_update_document(document: Document) -> None:
    document.status = "analysing"
    db.session.flush()
    try:
        result = analyze_document(
            path=document.path,
            original_filename=document.original_filename,
            mime_type=document.mime_type,
            base_url=current_app.config["OLLAMA_BASE_URL"],
            model=current_app.config["OLLAMA_MODEL"],
            timeout=current_app.config["OLLAMA_TIMEOUT_SECONDS"],
        )
    except Exception as exc:  # Ollama is optional at runtime; keep the upload usable.
        document.status = "analysis_failed"
        document.error = str(exc)
        return

    document.status = "analysed"
    document.suggested_category = result.get("category") or ""
    document.suggested_amount = result.get("amount")
    document.suggested_vendor = str(result.get("vendor") or "")[:255]
    document.suggested_date = result.get("date")
    document.suggested_description = str(result.get("description") or "")[:2000]
    document.extracted_text = result.get("extracted_text") or ""
    document.analysis_json = _json_dumpable(result)
    document.error = ""


def _json_dumpable(result: dict[str, Any]) -> str:
    def default(value: Any) -> str:
        return str(value)

    return json.dumps(result, default=default, sort_keys=True)


def _decimal_form(name: str, default: Decimal = Decimal("0.00")) -> Decimal:
    return _decimal_value(request.form.get(name, ""), default)


def _decimal_value(value: str | None, default: Decimal = Decimal("0.00")) -> Decimal:
    if value is None or value.strip() == "":
        return default
    try:
        return Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError):
        return default


def _int_form(name: str, default: int = 0) -> int:
    try:
        return int(request.form.get(name, default))
    except (TypeError, ValueError):
        return default


def _date_form(name: str) -> date | None:
    value = request.form.get(name, "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
