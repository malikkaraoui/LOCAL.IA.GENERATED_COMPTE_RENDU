"""Helpers to format the deterministic {{LIEU_ET_DATE}} field."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

DEFAULT_DATE_FORMAT = "%d/%m/%Y"


def build_location_date(
    location: str,
    manual_value: str,
    *,
    auto_date: bool,
    reference_time: Optional[datetime] = None,
    date_format: str = DEFAULT_DATE_FORMAT,
) -> str:
    """Return the string used for {{LIEU_ET_DATE}}.

    When ``auto_date`` is True (or no manual value is provided), the current date
    is formatted using ``date_format`` and combined with the ``location``.
    Otherwise ``manual_value`` is returned as-is (stripped).
    """

    location = (location or "").strip()
    manual_value = (manual_value or "").strip()

    if auto_date or not manual_value:
        when = reference_time or datetime.now()
        formatted_date = when.strftime(date_format)
        if location:
            return f"{location}, le {formatted_date}"
        return formatted_date

    return manual_value
