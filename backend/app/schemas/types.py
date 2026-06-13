from datetime import datetime, timezone
from typing import Annotated

from pydantic import PlainSerializer


def _to_utc_iso(dt: datetime) -> str:
    """Serialize a datetime as UTC ISO-8601 with a 'Z' suffix.

    The app stores naive UTC timestamps, so a naive value is treated as UTC.
    Emitting an explicit offset means every client (web, extension, raw API)
    parses the instant correctly instead of guessing local time.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


# Use in place of `datetime` on schema fields. The serializer only runs on JSON
# output (`when_used="json"`), so request parsing/validation is unchanged.
UTCDateTime = Annotated[
    datetime,
    PlainSerializer(_to_utc_iso, return_type=str, when_used="json"),
]
