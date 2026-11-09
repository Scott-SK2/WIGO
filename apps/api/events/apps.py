from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = "events"
    verbose_name = "Événements"

    def ready(self):
        from . import signals  # noqa: F401
