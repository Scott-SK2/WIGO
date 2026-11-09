"""Erreurs structurées : {"error": {"code", "message", "details"}} (§9.2)."""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class BusinessRuleViolation(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "business_rule_violation"
    default_detail = "Règle métier non respectée."


class InvalidTransition(BusinessRuleViolation):
    default_code = "invalid_transition"
    default_detail = "Transition de statut non autorisée."


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data
    code = getattr(exc, "default_code", "error")
    codes = exc.get_codes() if hasattr(exc, "get_codes") else None
    if isinstance(detail, dict) and "detail" in detail:
        detail = dict(detail)
        message = str(detail.pop("detail"))
        details = detail or None
        if isinstance(codes, str):
            code = codes
        elif isinstance(codes, dict) and isinstance(codes.get("detail"), str):
            code = codes["detail"]
    elif isinstance(detail, dict):
        message = "Données invalides."
        details = detail
        code = "validation_error"
    else:
        message = str(detail)
        details = None
        if isinstance(codes, str):
            code = codes
    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
