from celery import shared_task

from .emails import send_templated


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_account_email(kind: str, to: str, lang: str, url: str, hours: int):
    send_templated(kind, to, lang, url=url, hours=hours)
