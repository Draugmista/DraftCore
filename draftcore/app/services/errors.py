from __future__ import annotations


class AppError(Exception):
    """Base application error with a user-facing category."""

    category = "application"


class ValidationError(AppError):
    category = "validation"


class NotFoundError(AppError):
    category = "not_found"


class UnsupportedFeatureError(AppError):
    category = "unsupported"
