"""Export iCalendar (UI-06, GET /api/v1/events/{slug}/ics)."""

from __future__ import annotations

from datetime import UTC, datetime

from django.conf import settings

from .models import Event, OccurrenceStatus


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    out, encoded = [], line.encode("utf-8")
    while len(encoded) > 73:
        cut = 73
        while cut > 0 and (encoded[cut] & 0xC0) == 0x80:  # ne pas couper un caractère UTF-8
            cut -= 1
        out.append(encoded[:cut].decode("utf-8"))
        encoded = b" " + encoded[cut:]
    out.append(encoded.decode("utf-8"))
    return "\r\n".join(out)


def _utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def event_to_ics(event: Event, public_url: str) -> str:
    now = datetime.now(UTC)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WIGO//Agenda//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(event.title)}",
    ]
    location = ""
    if event.venue_id:
        location = f"{event.venue.name}, {event.venue.address_line}"
    description = event.description.strip()
    if event.ticketing_url:
        description += f"\n\nBillets : {event.ticketing_url}"
    description += f"\n\n{public_url}"
    for occ in event.occurrences.all():
        status = (
            "CANCELLED"
            if occ.status == OccurrenceStatus.CANCELLED or event.status == "CANCELLED"
            else "CONFIRMED"
        )
        lines += [
            "BEGIN:VEVENT",
            f"UID:{event.id}-{occ.id}@wigo.be",
            f"DTSTAMP:{_utc(now)}",
            f"DTSTART:{_utc(occ.starts_at)}",
            f"DTEND:{_utc(occ.ends_at)}",
            f"SUMMARY:{_escape(event.title)}",
            f"DESCRIPTION:{_escape(description)}",
            f"URL:{public_url}",
            f"STATUS:{status}",
        ]
        if location:
            lines.append(f"LOCATION:{_escape(location)}")
        if event.venue_id and event.venue.location:
            lines.append(f"GEO:{event.venue.location.y:.6f};{event.venue.location.x:.6f}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def public_event_url(event: Event, lang: str = "fr") -> str:
    return f"{settings.PUBLIC_WEB_URL}/{lang}/evenements/{event.slug}"
