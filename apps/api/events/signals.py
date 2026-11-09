from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Event
from .search import refresh_search_vector


@receiver(post_save, sender=Event)
def _refresh_on_save(sender, instance: Event, **kwargs):
    if kwargs.get("raw"):
        return
    refresh_search_vector(instance)


@receiver(m2m_changed, sender=Event.tags.through)
def _refresh_on_tags(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear") and isinstance(instance, Event):
        refresh_search_vector(instance)
