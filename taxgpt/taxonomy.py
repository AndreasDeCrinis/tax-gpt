from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    code: str
    group: str
    label: str
    finanzonline_section: str
    hint: str
    question: str = ""
    default_deductible_percent: int = 100


GROUP_LABELS = {
    "income": "Einkünfte",
    "work_expense": "Werbungskosten",
    "special_expense": "Sonderausgaben",
    "extraordinary": "Außergewöhnliche Belastungen",
    "family_credit": "Familie und Absetzbeträge",
    "international": "International",
}


CATEGORIES: tuple[Category, ...] = (
    Category(
        "employment_income",
        "income",
        "Einkünfte aus nichtselbständiger Arbeit / Lohnzettel",
        "Lohnzettel und Datenübermittlungen",
        "Übermittelte Lohnzettel prüfen; nur fehlende oder korrigierte Werte in FinanzOnline erfassen.",
    ),
    Category(
        "self_employed_income",
        "income",
        "Selbständige Einkünfte",
        "E1 / E1a",
        "Für selbständige oder betriebliche Einkünfte die Bereiche E1 und E1a verwenden.",
    ),
    Category("business_income", "income", "Betriebliche Einkünfte", "E1 / E1a", "Beilage für betriebliche Einkünfte."),
    Category("rental_income", "income", "Einkünfte aus Vermietung", "E1 / E1b", "Beilage für Vermietung und Verpachtung."),
    Category("capital_income", "income", "Kapitaleinkünfte", "E1", "Kapitaleinkünfte, die nicht endbesteuert sind."),
    Category("foreign_income", "income", "Auslandseinkünfte", "L1i / E1", "Auslandseinkünfte oder grenzüberschreitende Angaben."),
    Category("pension_income", "income", "Pensionseinkünfte", "Lohnzettel und Datenübermittlungen", "Übermittelte Pensionslohnzettel prüfen."),
    Category(
        "work_equipment",
        "work_expense",
        "Arbeitsmittel und Werkzeuge",
        "Werbungskosten",
        "Arbeitsmittel/Werkzeuge; Rechnungen aufbewahren und Privatanteil berücksichtigen.",
        "Hast du Arbeitsmittel, Werkzeuge, Schreibtisch-Ausstattung oder ähnliche berufliche Dinge gekauft?",
    ),
    Category(
        "computer",
        "work_expense",
        "Computer, Software und Zubehör",
        "Werbungskosten",
        "Computer und Zubehör; beruflichen Anteil und gegebenenfalls Abschreibung berücksichtigen.",
        "Hast du Computer, Monitor, Handy, Software oder Zubehör beruflich genutzt oder gekauft?",
    ),
    Category(
        "home_office",
        "work_expense",
        "Homeoffice / Telearbeit",
        "Werbungskosten",
        "Homeoffice-/Telearbeitskosten und ergonomische Möbel, sofern begünstigt.",
        "Hast du im Homeoffice gearbeitet und dafür Kosten getragen?",
    ),
    Category(
        "workroom",
        "work_expense",
        "Arbeitszimmer",
        "Werbungskosten",
        "Arbeitszimmer nur bei Erfüllung der strengen Voraussetzungen.",
        "Hast du ein eigenes Arbeitszimmer, das Mittelpunkt deiner beruflichen Tätigkeit ist?",
    ),
    Category(
        "training",
        "work_expense",
        "Ausbildung, Fortbildung und Umschulung",
        "Werbungskosten",
        "Aus-, Fortbildungs- oder Umschulungskosten.",
        "Hast du berufliche Ausbildung, Fortbildung, Kurse, Prüfungen oder Umschulung bezahlt?",
    ),
    Category(
        "union_works_council",
        "work_expense",
        "Gewerkschaftsbeiträge / Betriebsratsumlage",
        "Werbungskosten",
        "Betriebsratsumlage oder Gewerkschaftsbeiträge, wenn nicht bereits über die Lohnverrechnung berücksichtigt.",
        "Hast du Gewerkschaftsbeiträge oder Betriebsratsumlage außerhalb der Lohnverrechnung bezahlt?",
    ),
    Category(
        "professional_clothing",
        "work_expense",
        "Berufskleidung",
        "Werbungskosten",
        "Nur typische Berufskleidung oder besondere Reinigungskosten, soweit begünstigt.",
        "Hast du vorgeschriebene Berufskleidung oder deren Reinigung bezahlt?",
    ),
    Category(
        "literature",
        "work_expense",
        "Fachliteratur",
        "Werbungskosten",
        "Fachliteratur mit direktem beruflichem Zusammenhang.",
        "Hast du berufliche Bücher, Fachzeitschriften oder bezahlte Recherchematerialien gekauft?",
    ),
    Category(
        "internet_phone",
        "work_expense",
        "Internet und Telefon",
        "Werbungskosten",
        "Beruflicher Anteil von Internet- oder Telefonkosten.",
        "Hast du privates Internet oder Telefon beruflich genutzt?",
    ),
    Category(
        "travel",
        "work_expense",
        "Berufliche Reisekosten",
        "Werbungskosten",
        "Reise, Unterkunft, Tagesgelder und nicht ersetzte berufliche Reisen.",
        "Hattest du nicht ersetzte berufliche Reisekosten?",
    ),
    Category(
        "mileage",
        "work_expense",
        "Kilometergeld / privates Fahrzeug beruflich",
        "Werbungskosten",
        "Kilometergeld oder tatsächliche Kosten für berufliche Fahrten, ausgenommen Arbeitsweg.",
        "Hast du Auto, Motorrad, Fahrrad oder öffentliche Verkehrsmittel für berufliche Fahrten genutzt?",
    ),
    Category(
        "double_household",
        "work_expense",
        "Doppelte Haushaltsführung / Familienheimfahrten",
        "Werbungskosten",
        "Doppelte Haushaltsführung und Familienheimfahrten.",
        "Hattest du aus beruflichen Gründen einen zweiten Haushalt oder Familienheimfahrten?",
    ),
    Category(
        "commuter_allowance",
        "work_expense",
        "Pendlerpauschale / Pendlereuro",
        "Pendlerpauschale/-euro",
        "Pendlerrechner-Ergebnis verwenden und fehlende Pendlerpauschale/Pendlereuro nachtragen.",
        "Wurde deine Pendlerpauschale oder dein Pendlereuro vom Arbeitgeber nicht oder zu niedrig berücksichtigt?",
    ),
    Category(
        "other_work_expense",
        "work_expense",
        "Sonstige berufliche Kosten",
        "Werbungskosten",
        "Sonstige beruflich veranlasste Kosten mit Nachweis.",
        "Hast du andere berufliche Kosten, die oben nicht abgedeckt sind?",
    ),
    Category(
        "tax_advice",
        "special_expense",
        "Steuerberatung",
        "Sonderausgaben",
        "Kosten für Steuerberatung, selbständige Bilanzbuchhaltung oder Personalverrechnung.",
        "Hast du Steuerberatung oder Hilfe bei der Steuererklärung bezahlt?",
    ),
    Category(
        "church_contribution",
        "special_expense",
        "Kirchenbeitrag",
        "Sonderausgaben",
        "Beiträge an Kirche oder Religionsgesellschaft; oft automatisch übermittelt.",
        "Hast du Kirchenbeiträge bezahlt, die nicht korrekt automatisch übermittelt wurden?",
    ),
    Category(
        "donations",
        "special_expense",
        "Spenden an begünstigte Organisationen",
        "Sonderausgaben",
        "Begünstigte inländische Spenden; viele werden automatisch übermittelt.",
        "Hast du an begünstigte Organisationen, Feuerwehren oder Katastrophenhilfe gespendet?",
    ),
    Category(
        "foreign_donations",
        "special_expense",
        "Ausländische Spenden / ausländische Kirchenbeiträge",
        "Besondere Sonderausgaben (L1d)",
        "Ausländische Spenden oder Kirchenbeiträge können eine manuelle L1d-Eingabe erfordern.",
        "Hast du ausländische Spenden oder ausländische Kirchenbeiträge geleistet?",
    ),
    Category(
        "voluntary_insurance",
        "special_expense",
        "Freiwillige Weiterversicherung / Nachkauf von Versicherungszeiten",
        "Besondere Sonderausgaben (L1d)",
        "Nachkauf von Versicherungszeiten oder freiwillige Weiterversicherung.",
        "Hast du freiwillige Weiterversicherung bezahlt oder Versicherungszeiten nachgekauft?",
    ),
    Category(
        "eco_renovation",
        "special_expense",
        "Öko-Sanierung / Heizungstausch",
        "Sonderausgaben",
        "Thermisch-energetische Sanierung oder klimafreundlicher Heizungstausch.",
        "Hast du energetisch saniert oder ein fossiles Heizsystem ersetzt?",
    ),
    Category(
        "special_other",
        "special_expense",
        "Sonstige Sonderausgaben",
        "Sonderausgaben",
        "Sonstige Sonderausgaben mit Nachweis.",
        "Hast du sonstige Sonderausgaben?",
    ),
    Category(
        "medical_costs",
        "extraordinary",
        "Krankheitskosten",
        "Außergewöhnliche Belastungen (L1ab)",
        "Krankheitskosten nach Abzug von Ersätzen; ein Selbstbehalt kann gelten.",
        "Hast du nicht ersetzte Arzt-, Therapie-, Medikamenten-, Brillen-, Zahn- oder Krankenhauskosten bezahlt?",
    ),
    Category(
        "spa_costs",
        "extraordinary",
        "Kur- und Rehabilitationskosten",
        "Außergewöhnliche Belastungen (L1ab)",
        "Kurkosten nach Abzug von Ersätzen, wenn medizinisch erforderlich.",
        "Hast du eine medizinisch erforderliche Kur oder Rehabilitation bezahlt?",
    ),
    Category(
        "funeral_costs",
        "extraordinary",
        "Begräbniskosten",
        "Außergewöhnliche Belastungen (L1ab)",
        "Begräbniskosten nur soweit nicht durch Nachlass oder Versicherung gedeckt.",
        "Hast du Begräbniskosten getragen, die nicht durch Nachlass oder Versicherung gedeckt waren?",
    ),
    Category(
        "disaster_damage",
        "extraordinary",
        "Katastrophenschäden",
        "Außergewöhnliche Belastungen (L1ab)",
        "Katastrophenschäden nach Abzug von Ersätzen.",
        "Hattest du Kosten durch Hochwasser, Sturm, Brand oder andere Katastrophenschäden?",
    ),
    Category(
        "care_costs",
        "extraordinary",
        "Pflege- und Betreuungskosten",
        "Außergewöhnliche Belastungen (L1ab)",
        "Pflege-/Betreuungskosten nach Abzug von Pflegegeld und Ersätzen.",
        "Hast du Pflege, Betreuung oder betreutes Wohnen bezahlt?",
    ),
    Category(
        "disability_aids",
        "extraordinary",
        "Hilfsmittel und Heilbehandlung bei Behinderung",
        "Außergewöhnliche Belastungen bei Behinderung (L1ab)",
        "Hilfsmittel, Heilbehandlung und behinderungsbedingte Kosten.",
        "Hast du Kosten im Zusammenhang mit eigener Behinderung, Behinderung des Partners oder eines Kindes bezahlt?",
    ),
    Category(
        "disability_lump_sum",
        "extraordinary",
        "Freibeträge bei Behinderung / Diät",
        "Außergewöhnliche Belastungen bei Behinderung (L1ab)",
        "Grad der Behinderung, Diätpauschale, KFZ-Pauschale oder Pflegegeldangaben.",
        "Hast du einen Behinderungsgrad, Diäterfordernis, Pflegegeld oder eine behinderungsbedingte KFZ-Pauschale?",
    ),
    Category(
        "child_care",
        "extraordinary",
        "Kinderbetreuung und kinderbezogene Kosten",
        "Kinder (L1k)",
        "Kinderbetreuung oder kinderbezogene außergewöhnliche Belastungen, soweit begünstigt.",
        "Hast du Kinderbetreuung oder andere steuerlich relevante Kosten für Kinder bezahlt?",
    ),
    Category(
        "child_outside_education",
        "extraordinary",
        "Auswärtige Berufsausbildung eines Kindes",
        "Kinder (L1k)",
        "Auswärtige Berufsausbildung eines Kindes.",
        "Hat ein Kind auswärts studiert oder eine Ausbildung gemacht, weil es keine gleichwertige lokale Möglichkeit gab?",
    ),
    Category(
        "dependent_support",
        "extraordinary",
        "Unterstützung für Unterhaltsberechtigte",
        "Außergewöhnliche Belastungen / Kinder (L1k)",
        "Steuerlich relevante Unterstützungs- oder Unterhaltsleistungen.",
        "Hast du steuerlich relevante Unterstützungs- oder Unterhaltskosten bezahlt?",
    ),
    Category(
        "extraordinary_other",
        "extraordinary",
        "Sonstige außergewöhnliche Belastungen",
        "Außergewöhnliche Belastungen (L1ab)",
        "Sonstige zwangsläufige außergewöhnliche Kosten.",
        "Hast du andere zwangsläufige außergewöhnliche Kosten?",
    ),
    Category(
        "family_bonus_plus",
        "family_credit",
        "Familienbonus Plus",
        "Kinder (L1k)",
        "Familienbonus Plus pro Kind, soweit nicht bereits vollständig in der Lohnverrechnung berücksichtigt.",
        "Möchtest du den Familienbonus Plus beantragen oder anpassen?",
    ),
    Category(
        "single_earner_parent",
        "family_credit",
        "Alleinverdiener-/Alleinerzieherabsetzbetrag",
        "Allgemeine Daten",
        "Alleinverdiener- oder Alleinerzieherabsetzbetrag.",
        "Könnte dir der Alleinverdiener- oder Alleinerzieherabsetzbetrag zustehen?",
    ),
    Category(
        "alimony_credit",
        "family_credit",
        "Unterhaltsabsetzbetrag",
        "Kinder (L1k)",
        "Unterhaltsabsetzbetrag für begünstigte Unterhaltszahlungen.",
        "Hast du Unterhalt für ein Kind gezahlt, das nicht in deinem Haushalt lebt?",
    ),
)

CATEGORY_BY_CODE = {category.code: category for category in CATEGORIES}


def get_category(code: str) -> Category:
    return CATEGORY_BY_CODE.get(
        code,
        Category(code, "other", code.replace("_", " ").title(), "Sonstige Angaben", "Manuell prüfen."),
    )


def categories_for_select() -> list[Category]:
    return sorted(CATEGORIES, key=lambda item: (GROUP_LABELS.get(item.group, item.group), item.label))


def deduction_questions() -> list[Category]:
    return [category for category in CATEGORIES if category.question]
