from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import (
    ImportRun,
    ImportRunStatus,
    ImportSource,
    NewsletterSubscription,
    SendStatus,
    SubscriptionStatus,
    WeekendSelection,
)

NEWSLETTER_SUBJECT = {
    "fr": "Ce week-end à Bruxelles — la sélection WIGO",
    "nl": "Dit weekend in Brussel — de WIGO-selectie",
    "en": "This weekend in Brussels — the WIGO selection",
}


@shared_task
def send_newsletter_confirmation(subscription_id: str) -> None:
    sub = NewsletterSubscription.objects.filter(pk=subscription_id).first()
    if sub is None:
        return
    url = (
        f"{settings.PUBLIC_WEB_URL}/{sub.language}/newsletter/confirmation"
        f"?token={sub.confirm_token}"
    )
    body = {
        "fr": f"Confirmez votre inscription à « Ce week-end à Bruxelles » :\n{url}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.",
        "nl": f"Bevestig je inschrijving voor « Dit weekend in Brussel »:\n{url}",
        "en": f"Confirm your subscription to « This weekend in Brussels »:\n{url}",
    }[sub.language]
    send_mail("WIGO — confirmez votre inscription", body, settings.DEFAULT_FROM_EMAIL, [sub.email])


def render_newsletter(selection: WeekendSelection, lang: str, unsubscribe_url: str) -> str:
    lines = [selection.title or NEWSLETTER_SUBJECT[lang], ""]
    if selection.intro:
        lines += [selection.intro, ""]
    for item in selection.items.select_related("event__venue", "event__primary_category"):
        ev = item.event
        occ = ev.occurrences.filter(status="SCHEDULED").order_by("starts_at").first()
        when = (
            occ.starts_at.astimezone(timezone.get_default_timezone()).strftime("%a %d/%m %H:%M")
            if occ
            else ""
        )
        where = ev.venue.name if ev.venue_id else "En ligne"
        lines.append(f"• {ev.title} — {when} — {where}")
        if item.blurb:
            lines.append(f"  {item.blurb}")
        lines.append(f"  {settings.PUBLIC_WEB_URL}/{lang}/evenements/{ev.slug}")
        lines.append("")
    lines += [
        "—",
        "Les événements « Partenaire » ou « Sélection WIGO » sont signalés comme tels (RG-28).",
        f"Se désinscrire en un clic : {unsubscribe_url}",
    ]
    return "\n".join(lines)


@shared_task
def send_weekly_newsletter(selection_id: int | None = None) -> int:
    """RET-02 : newsletter du jeudi générée depuis la sélection du week-end."""
    selection = (
        WeekendSelection.objects.filter(pk=selection_id).first()
        if selection_id
        else WeekendSelection.objects.filter(send_status=SendStatus.READY)
        .order_by("-week_start")
        .first()
    )
    if (
        selection is None
        or selection.send_status == SendStatus.SENT
        or not selection.items.exists()
    ):
        return 0
    sent = 0
    for sub in NewsletterSubscription.objects.filter(
        status=SubscriptionStatus.CONFIRMED
    ).iterator():
        unsub = (
            f"{settings.PUBLIC_WEB_URL}/{sub.language}/newsletter/desinscription"
            f"?token={sub.unsubscribe_token}"
        )
        send_mail(
            NEWSLETTER_SUBJECT[sub.language],
            render_newsletter(selection, sub.language, unsub),
            settings.DEFAULT_FROM_EMAIL,
            [sub.email],
        )
        sent += 1
    selection.send_status = SendStatus.SENT
    selection.sent_at = timezone.now()
    selection.recipients_count = sent
    selection.save(update_fields=["send_status", "sent_at", "recipients_count", "updated_at"])
    return sent


@shared_task
def run_import(source_id: int, user_id: str | None = None) -> int:
    """CAT-02 : exécution d'un import partenaire. Les connecteurs sont dans engagement.importers."""
    from .importers import get_importer

    source = ImportSource.objects.get(pk=source_id)
    run = ImportRun.objects.create(source=source, triggered_by_id=user_id)
    try:
        importer = get_importer(source)
        result = importer.run()
        run.created_count, run.updated_count, run.skipped_count = (
            result.created,
            result.updated,
            result.skipped,
        )
        run.log = "\n".join(result.log[-200:])
        run.status = ImportRunStatus.SUCCESS
    except Exception as exc:  # noqa: BLE001
        run.status = ImportRunStatus.FAILED
        run.log = f"{type(exc).__name__}: {exc}"
    run.finished_at = timezone.now()
    run.save()
    source.last_run_at = run.finished_at
    source.save(update_fields=["last_run_at"])
    return run.pk
