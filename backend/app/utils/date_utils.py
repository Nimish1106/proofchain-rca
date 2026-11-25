"""Date and numeric normalization helpers for consistent persistence."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_ORDINAL_SUFFIX_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b", re.IGNORECASE)

_ACCEPTED_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%d-%B-%Y",
    "%d-%b-%Y",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
)


def parse_incident_date(value: date | datetime | str) -> date:
    """
    Parse ISO and common document date formats into a datetime.date.
    Raises ValueError if the input cannot be parsed as a calendar date.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("Date must be a string or date object.")

    cleaned = re.sub(r"\s+", " ", value.strip())
    if not cleaned:
        raise ValueError("Date cannot be empty.")

    # Normalize ordinal suffixes like "20th November 2026" -> "20 November 2026"
    cleaned = _ORDINAL_SUFFIX_RE.sub(r"\1", cleaned)

    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        pass

    for fmt in _ACCEPTED_DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    raise ValueError(
        f"Unrecognized date format '{value}'. Expected YYYY-MM-DD or standard calendar date."
    )


def normalize_incident_date(value: date | datetime | str) -> str:
    """Return canonical ISO YYYY-MM-DD date string."""
    return parse_incident_date(value).isoformat()


def parse_affected_quantity(value: Decimal | int | float | str) -> Decimal:
    """Parse numeric quantity values, tolerating thousands separators."""
    if isinstance(value, Decimal):
        return value
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        raise ValueError("Quantity cannot be empty.")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric quantity: {value}") from exc
