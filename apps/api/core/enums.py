"""Énumérations partagées entre les apps (statuts et niveaux, §5.4 et §6)."""

from django.db import models


class TrustLevel(models.TextChoices):
    NEW = "NEW", "Nouveau"
    CONFIRMED = "CONFIRMED", "Confirmé"
    VERIFIED = "VERIFIED", "Vérifié"


class Language(models.TextChoices):
    FR = "fr", "Français"
    NL = "nl", "Nederlands"
    EN = "en", "English"
