"""Journalisation des actions sensibles (§3, ADM-05)."""

from __future__ import annotations

from typing import Any


def log_action(
    actor,
    action: str,
    target,
    *,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    note: str = "",
):
    from moderation.models import AuditLog

    return AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        action=action,
        target_type=target.__class__.__name__ if target is not None else "",
        target_id=str(getattr(target, "pk", "") or ""),
        before=before or {},
        after=after or {},
        note=note,
    )
