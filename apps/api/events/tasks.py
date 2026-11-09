"""Tâches asynchrones (§8.1) : archivage, relances fraîcheur, notifications, médias."""

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Max
from django.utils import timezone

from .models import Event, EventStatus, OccurrenceStatus


@shared_task
def archive_finished_events() -> int:
    """TRU-02 : archivage automatique après la dernière séance."""
    from . import workflow

    now = timezone.now()
    qs = (
        Event.objects.filter(status__in=[EventStatus.PUBLISHED, EventStatus.CANCELLED])
        .annotate(last_end=Max("occurrences__ends_at"))
        .filter(last_end__lt=now - timedelta(hours=6))
    )
    count = 0
    for event in qs:
        workflow.archive(event, actor=None)
        count += 1
    return count


@shared_task
def send_freshness_reminders() -> int:
    """§5.7 : e-mail à l'organisateur 72 h avant chaque séance (Confirmer / Annuler / Modifier)."""
    now = timezone.now()
    horizon = now + timedelta(hours=settings.WIGO_RULES["FRESHNESS_REMINDER_HOURS"])
    qs = (
        Event.objects.filter(
            status=EventStatus.PUBLISHED,
            occurrences__status=OccurrenceStatus.SCHEDULED,
            occurrences__starts_at__range=(now, horizon),
            source__in=["MANUAL", "INTERNAL"],
        )
        .filter(freshness_reminder_sent_at__isnull=True)
        .distinct()
        .select_related("owner_user")
    )
    sent = 0
    for event in qs:
        if event.last_confirmed_at and event.last_confirmed_at > now - timedelta(days=5):
            continue
        url = f"{settings.PUBLIC_WEB_URL}/{event.owner_user.language}/espace/evenements/{event.id}"
        send_mail(
            f"[WIGO] Votre événement « {event.title} » a lieu bientôt : tout est correct ?",
            "Merci de confirmer que les informations sont à jour, ou d'annuler / modifier "
            f"l'événement :\n{url}\n\nWIGO — Trouve ta prochaine sortie.",
            settings.DEFAULT_FROM_EMAIL,
            [event.owner_user.email],
        )
        event.freshness_reminder_sent_at = now
        event.save(update_fields=["freshness_reminder_sent_at"])
        sent += 1
    return sent


@shared_task
def notify_favorites_of_change(event_id: str) -> int:
    """RG-11 : notification des personnes ayant l'événement en favori."""
    event = Event.objects.filter(pk=event_id).select_related("owner_user").first()
    if event is None:
        return 0
    emails = list(
        event.favorites.filter(user__notify_favorite_reminders=True).values_list(
            "user__email", flat=True
        )
    )
    if not emails:
        return 0
    url = f"{settings.PUBLIC_WEB_URL}/fr/evenements/{event.slug}"
    send_mail(
        f"[WIGO] « {event.title} » a été modifié",
        f"Un événement de vos favoris a changé (date, lieu ou conditions). Détails :\n{url}",
        settings.DEFAULT_FROM_EMAIL,
        emails,
    )
    return len(emails)


@shared_task
def notify_favorites_of_cancellation(event_id: str) -> int:
    event = Event.objects.filter(pk=event_id).first()
    if event is None:
        return 0
    emails = list(event.favorites.values_list("user__email", flat=True))
    if emails:
        url = f"{settings.PUBLIC_WEB_URL}/fr/evenements/{event.slug}"
        send_mail(
            f"[WIGO] « {event.title} » est annulé",
            f"Un événement de vos favoris a été annulé par l'organisateur.\n{url}",
            settings.DEFAULT_FROM_EMAIL,
            emails,
        )
    return len(emails)


@shared_task
def process_media(media_id: int) -> None:
    """EVT-06 : suppression des métadonnées EXIF, limitation de taille, dimensions."""
    from io import BytesIO

    from django.core.files.base import ContentFile
    from PIL import Image, ImageOps

    from .models import EventMedia

    media = EventMedia.objects.filter(pk=media_id).first()
    if media is None:
        return
    with media.image.open("rb") as fh:
        img = Image.open(fh)
        img = ImageOps.exif_transpose(img)  # applique l'orientation puis on repart sans EXIF
        img = img.convert("RGB")
        img.thumbnail((2000, 2000))
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=85, method=6)
    name = media.image.name.rsplit(".", 1)[0] + ".webp"
    media.image.save(name, ContentFile(buf.getvalue()), save=False)
    media.width, media.height = img.size
    media.save(update_fields=["image", "width", "height"])
