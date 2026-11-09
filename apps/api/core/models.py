import uuid

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TranslatedNameMixin(models.Model):
    """Nom en FR / NL / EN avec repli sur le français (§2.1 Langues)."""

    name_fr = models.CharField(max_length=120)
    name_nl = models.CharField(max_length=120, blank=True)
    name_en = models.CharField(max_length=120, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name_fr

    def name(self, lang: str = "fr") -> str:
        return getattr(self, f"name_{lang}", "") or self.name_fr

    @property
    def names(self) -> dict:
        return {
            "fr": self.name_fr,
            "nl": self.name_nl or self.name_fr,
            "en": self.name_en or self.name_fr,
        }
