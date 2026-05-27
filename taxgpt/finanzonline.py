from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .models import TaxYear


@dataclass(frozen=True)
class FinanzOnlineOption:
    value: str
    label: str


@dataclass(frozen=True)
class FinanzOnlineField:
    key: str
    code: str
    label: str
    input_type: str = "money"
    hint: str = ""
    linked_categories: tuple[str, ...] = ()
    placeholder: str = ""
    options: tuple[FinanzOnlineOption, ...] = ()


@dataclass(frozen=True)
class FinanzOnlineSection:
    title: str
    subtitle: str
    fields: tuple[FinanzOnlineField, ...]


PROFESSION_OPTIONS = (
    FinanzOnlineOption("", "Bitte auswählen"),
    FinanzOnlineOption("A", "Artistinnen/Artisten, Bühnenangehörige, Filmschauspielerinnen/-schauspieler"),
    FinanzOnlineOption("B", "Forstarbeiterinnen/Forstarbeiter ohne Motorsäge"),
    FinanzOnlineOption("F", "Forstarbeiterinnen/Forstarbeiter mit Motorsäge"),
    FinanzOnlineOption("H", "Hausbesorgerinnen/Hausbesorger"),
    FinanzOnlineOption("J", "Journalistinnen/Journalisten"),
    FinanzOnlineOption("M", "Musikerinnen/Musiker"),
    FinanzOnlineOption("P", "Politikerinnen/Politiker"),
    FinanzOnlineOption("V", "Vertreterinnen/Vertreter"),
)


FINANZONLINE_SECTIONS = (
    FinanzOnlineSection(
        "Pendlerpauschale / Pendlereuro",
        "Nur ausfüllen, wenn der Betrag nicht bereits durch den Arbeitgeber in richtiger Höhe berücksichtigt wurde.",
        (
            FinanzOnlineField(
                "fo_718",
                "718",
                "Pendlerpauschale - tatsächlich zustehender Gesamtjahresbetrag abzüglich Kostenersatz für Öffi-Ticket",
                hint="Berechnung laut Pendlerrechner unter bmf.gv.at/pendlerrechner.",
                linked_categories=("commuter_allowance",),
            ),
            FinanzOnlineField(
                "fo_916",
                "916",
                "Pendlereuro (Absetzbetrag) - tatsächlich zustehender Gesamtjahresbetrag",
                hint="Gemeinsam mit Kennzahl 718 ausfüllen, wenn relevant.",
                linked_categories=("commuter_euro",),
            ),
        ),
    ),
    FinanzOnlineSection(
        "Werbungskosten ohne Anrechnung auf das Werbungskostenpauschale",
        "Diese Kennzahlen werden nicht auf das allgemeine Werbungskostenpauschale angerechnet.",
        (
            FinanzOnlineField(
                "fo_717",
                "717",
                "Gewerkschaftsbeiträge und Beiträge zu Berufsverbänden/Interessensvertretungen",
                hint="Ausgenommen Betriebsratsumlage; nur wenn nicht bereits im Lohnzettel richtig berücksichtigt.",
                linked_categories=("union_works_council",),
            ),
            FinanzOnlineField(
                "fo_158",
                "158",
                "Ergonomisch geeignetes Mobiliar für Telearbeit bei zumindest 26 Telearbeitstagen",
                hint="Nicht gemeinsam mit Kennzahl 159 eintragen.",
                linked_categories=("home_office",),
            ),
            FinanzOnlineField(
                "fo_274",
                "274",
                "Pflichtbeiträge bei geringfügiger Beschäftigung, mitversicherte Angehörige oder selbst einbezahlte Sozialversicherungsbeiträge",
                linked_categories=("social_insurance",),
            ),
        ),
    ),
    FinanzOnlineSection(
        "Weitere Werbungskosten mit Anrechnung auf das Werbungskostenpauschale",
        "Jahresbetrag der Aufwendungen abzüglich steuerfreier Ersätze oder Vergütungen eintragen.",
        (
            FinanzOnlineField(
                "fo_occupation",
                "",
                "Genaue Bezeichnung der beruflichen Tätigkeit",
                input_type="text",
                placeholder="z.B. Technischer Angestellter",
            ),
            FinanzOnlineField(
                "fo_169",
                "169",
                "Digitale Arbeitsmittel (z.B. Computer, Internet)",
                hint="Bei Anschaffungen über 1.000 Euro inkl. Umsatzsteuer nur die jährliche Abschreibung eintragen.",
                linked_categories=("computer", "internet_phone"),
            ),
            FinanzOnlineField(
                "fo_719",
                "719",
                "Andere Arbeitsmittel, die nicht in Kennzahl 169 zu erfassen sind",
                hint="Bei Anschaffungen über 1.000 Euro inkl. Umsatzsteuer nur die jährliche Abschreibung eintragen.",
                linked_categories=("work_equipment", "professional_clothing"),
            ),
            FinanzOnlineField(
                "fo_720",
                "720",
                "Fachliteratur",
                hint="Keine allgemein bildenden Werke wie Lexika, Nachschlagewerke oder Zeitungen.",
                linked_categories=("literature",),
            ),
            FinanzOnlineField(
                "fo_721",
                "721",
                "Beruflich veranlasste Reisekosten",
                hint="Ohne Fahrtkosten Wohnung/Arbeitsstätte und ohne Familienheimfahrten.",
                linked_categories=("travel", "mileage"),
            ),
            FinanzOnlineField(
                "fo_722",
                "722",
                "Fortbildungs-, Ausbildungs- und Umschulungskosten",
                linked_categories=("training",),
            ),
            FinanzOnlineField(
                "fo_300",
                "300",
                "Kosten für Familienheimfahrten",
                linked_categories=("family_home_trips",),
            ),
            FinanzOnlineField(
                "fo_723",
                "723",
                "Kosten für doppelte Haushaltsführung",
                linked_categories=("double_household",),
            ),
            FinanzOnlineField(
                "fo_159",
                "159",
                "Arbeitszimmer",
                hint="Nicht gemeinsam mit Kennzahl 158 eintragen; nur wenn das Arbeitszimmer Mittelpunkt der Tätigkeit ist.",
                linked_categories=("workroom",),
            ),
            FinanzOnlineField(
                "fo_724",
                "724",
                "Sonstige Werbungskosten",
                hint="Nicht Kennzahlen 169, 719, 720, 721, 722, 300, 723 und 159; z.B. Betriebsratsumlage.",
                linked_categories=("other_work_expense",),
            ),
        ),
    ),
    FinanzOnlineSection(
        "Berufsgruppenpauschale",
        "Nur ausfüllen, wenn ein Berufsgruppenpauschale geltend gemacht wird.",
        (
            FinanzOnlineField("fo_profession_1", "", "Beruf 1", input_type="select", options=PROFESSION_OPTIONS),
            FinanzOnlineField("fo_profession_1_from", "", "Zeitraum der Tätigkeit 1: von (TTMM)", input_type="text", placeholder="TTMM"),
            FinanzOnlineField("fo_profession_1_to", "", "Zeitraum der Tätigkeit 1: bis (TTMM)", input_type="text", placeholder="TTMM"),
            FinanzOnlineField("fo_437", "437", "Erhaltene Kostenersätze für Beruf 1 ausgenommen Telearbeitspauschale"),
            FinanzOnlineField("fo_profession_2", "", "Beruf 2", input_type="select", options=PROFESSION_OPTIONS),
            FinanzOnlineField("fo_profession_2_from", "", "Zeitraum der Tätigkeit 2: von (TTMM)", input_type="text", placeholder="TTMM"),
            FinanzOnlineField("fo_profession_2_to", "", "Zeitraum der Tätigkeit 2: bis (TTMM)", input_type="text", placeholder="TTMM"),
            FinanzOnlineField("fo_438", "438", "Erhaltene Kostenersätze für Beruf 2 ausgenommen Telearbeitspauschale"),
        ),
    ),
)

FINANZONLINE_FIELD_BY_KEY = {field.key: field for section in FINANZONLINE_SECTIONS for field in section.fields}
CATEGORY_FIELD_BY_CODE = {
    category: field for field in FINANZONLINE_FIELD_BY_KEY.values() for category in field.linked_categories
}


def finanzonline_values(tax_year: TaxYear) -> dict[str, str]:
    values = tax_year.facts.get("finanzonline_fields", {})
    return values if isinstance(values, dict) else {}


def build_finanzonline_entry_totals(tax_year: TaxYear) -> dict[str, Decimal]:
    suggestions: dict[str, Decimal] = {}
    for field in FINANZONLINE_FIELD_BY_KEY.values():
        if field.input_type != "money" or not field.linked_categories:
            continue
        total = Decimal("0.00")
        for entry in tax_year.entries:
            if entry.category in field.linked_categories:
                total += entry.deductible_amount
        if total:
            suggestions[field.key] = total.quantize(Decimal("0.01"))
    return suggestions


def build_finanzonline_transfer_values(tax_year: TaxYear) -> dict[str, str]:
    manual_values = finanzonline_values(tax_year)
    entry_totals = build_finanzonline_entry_totals(tax_year)
    transfer_values: dict[str, str] = {}

    for key, field in FINANZONLINE_FIELD_BY_KEY.items():
        if field.input_type == "money" and field.linked_categories:
            if key in entry_totals:
                transfer_values[key] = format_money(entry_totals[key])
            continue
        manual_value = manual_values.get(key, "").strip()
        if manual_value:
            transfer_values[key] = manual_value

    return transfer_values


def build_finanzonline_value_sources(tax_year: TaxYear) -> dict[str, str]:
    manual_values = finanzonline_values(tax_year)
    entry_totals = build_finanzonline_entry_totals(tax_year)
    sources: dict[str, str] = {}
    for key in FINANZONLINE_FIELD_BY_KEY:
        field = FINANZONLINE_FIELD_BY_KEY[key]
        if field.input_type == "money" and field.linked_categories:
            if key in entry_totals:
                sources[key] = "Einzelbelege"
        elif manual_values.get(key, "").strip():
            sources[key] = "Manuell"
        elif key in entry_totals:
            sources[key] = "Einzelbelege"
    return sources


def format_money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):.2f}"


def normalise_money(value: str) -> str:
    if not value.strip():
        return ""
    try:
        return format_money(Decimal(value.replace(",", ".")))
    except (InvalidOperation, ValueError):
        return value.strip()


def kennzahl_for_category(category_code: str) -> str:
    field = CATEGORY_FIELD_BY_CODE.get(category_code)
    return field.code if field else ""


def category_display_label(category_code: str, label: str) -> str:
    kennzahl = kennzahl_for_category(category_code)
    return f"Kennzahl {kennzahl} - {label}" if kennzahl else label
