"""E-mails transactionnels FR / NL / EN (MAIL-01). Envoyés via Celery."""

from django.conf import settings
from django.core.mail import send_mail

SUBJECTS = {
    "verify": {
        "fr": "Confirmez votre adresse e-mail WIGO",
        "nl": "Bevestig je WIGO e-mailadres",
        "en": "Confirm your WIGO e-mail address",
    },
    "reset": {
        "fr": "Réinitialisation de votre mot de passe WIGO",
        "nl": "Je WIGO-wachtwoord opnieuw instellen",
        "en": "Reset your WIGO password",
    },
}
BODIES = {
    "verify": {
        "fr": "Bienvenue sur WIGO !\n\nConfirmez votre adresse en ouvrant ce lien :\n{url}\n\n"
        "Le lien est valable {hours} h.\n\nWIGO — Trouve ta prochaine sortie.",
        "nl": "Welkom bij WIGO!\n\nBevestig je adres via deze link:\n{url}\n\n"
        "De link is {hours} uur geldig.\n\nWIGO — Vind je volgende uitje.",
        "en": "Welcome to WIGO!\n\nConfirm your address by opening this link:\n{url}\n\n"
        "The link is valid for {hours} hours.\n\nWIGO — Find your next night out.",
    },
    "reset": {
        "fr": "Pour choisir un nouveau mot de passe, ouvrez ce lien :\n{url}\n\n"
        "Le lien est valable {hours} h. Si vous n'êtes pas à l'origine de cette demande, "
        "ignorez ce message.",
        "nl": "Kies een nieuw wachtwoord via deze link:\n{url}\n\n"
        "De link is {hours} uur geldig. Vroeg je dit niet aan, negeer dan dit bericht.",
        "en": "To choose a new password, open this link:\n{url}\n\n"
        "The link is valid for {hours} hours. If you did not request this, ignore this message.",
    },
}


def send_templated(kind: str, to: str, lang: str, **ctx) -> None:
    lang = lang if lang in ("fr", "nl", "en") else "fr"
    send_mail(
        SUBJECTS[kind][lang],
        BODIES[kind][lang].format(**ctx),
        settings.DEFAULT_FROM_EMAIL,
        [to],
        fail_silently=False,
    )
