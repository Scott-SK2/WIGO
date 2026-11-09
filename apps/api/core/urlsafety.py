"""Validation des URL externes : HTTPS, pas d'adresses internes (SSRF), liste blanche (RG-21)."""

import ipaddress
from urllib.parse import urlparse

from django.core.exceptions import ValidationError


def validate_https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise ValidationError("L'URL doit être en HTTPS.")
    host = (parsed.hostname or "").lower()
    if not host or "." not in host:
        raise ValidationError("Nom d'hôte invalide.")
    if host in {"localhost"} or host.endswith(".local") or host.endswith(".internal"):
        raise ValidationError("Hôte non autorisé.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return value
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise ValidationError("Adresse IP non autorisée.")
    return value


def registrable_domain(url: str) -> str:
    """Domaine sans www. (approximation suffisante pour la liste blanche)."""
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host
