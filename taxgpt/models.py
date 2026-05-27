from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, MetaData, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=convention))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(db.String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    tax_years: Mapped[list["TaxYear"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="TaxYear.year.desc()"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class TaxYear(db.Model):
    __tablename__ = "tax_years"
    __table_args__ = (UniqueConstraint("user_id", "year", name="uq_tax_year_user_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(nullable=False)
    filing_kind: Mapped[str] = mapped_column(db.String(80), default="arbeitnehmerveranlagung")
    facts_json: Mapped[str] = mapped_column(db.Text, default="{}")
    notes: Mapped[str] = mapped_column(db.Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="tax_years")
    entries: Mapped[list["TaxEntry"]] = relationship(
        back_populates="tax_year", cascade="all, delete-orphan", order_by="TaxEntry.created_at.desc()"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="tax_year", cascade="all, delete-orphan", order_by="Document.created_at.desc()"
    )

    @property
    def facts(self) -> dict[str, Any]:
        try:
            return json.loads(self.facts_json or "{}")
        except json.JSONDecodeError:
            return {}

    def set_facts(self, facts: dict[str, Any]) -> None:
        self.facts_json = json.dumps(facts, sort_keys=True)


class TaxEntry(db.Model):
    __tablename__ = "tax_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    tax_year_id: Mapped[int] = mapped_column(ForeignKey("tax_years.id"), nullable=False, index=True)
    group: Mapped[str] = mapped_column(db.String(40), nullable=False, index=True)
    category: Mapped[str] = mapped_column(db.String(80), nullable=False, index=True)
    label: Mapped[str] = mapped_column(db.String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    deductible_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("100.00"), nullable=False)
    paid_on: Mapped[date | None] = mapped_column(db.Date)
    vendor: Mapped[str] = mapped_column(db.String(255), default="")
    description: Mapped[str] = mapped_column(db.Text, default="")
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    tax_year: Mapped[TaxYear] = relationship(back_populates="entries")
    document: Mapped["Document | None"] = relationship(back_populates="entries")

    @property
    def deductible_amount(self) -> Decimal:
        return (self.amount or Decimal("0")) * (self.deductible_percent or Decimal("0")) / Decimal("100")


class Document(db.Model):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    tax_year_id: Mapped[int] = mapped_column(ForeignKey("tax_years.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(db.String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(db.String(255), nullable=False)
    path: Mapped[str] = mapped_column(db.String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(db.String(120), default="")
    size_bytes: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(db.String(40), default="uploaded", index=True)
    suggested_category: Mapped[str] = mapped_column(db.String(80), default="")
    suggested_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    suggested_vendor: Mapped[str] = mapped_column(db.String(255), default="")
    suggested_date: Mapped[date | None] = mapped_column(db.Date)
    suggested_description: Mapped[str] = mapped_column(db.Text, default="")
    extracted_text: Mapped[str] = mapped_column(db.Text, default="")
    analysis_json: Mapped[str] = mapped_column(db.Text, default="{}")
    error: Mapped[str] = mapped_column(db.Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    tax_year: Mapped[TaxYear] = relationship(back_populates="documents")
    entries: Mapped[list[TaxEntry]] = relationship(back_populates="document")

    @property
    def analysis(self) -> dict[str, Any]:
        try:
            return json.loads(self.analysis_json or "{}")
        except json.JSONDecodeError:
            return {}
