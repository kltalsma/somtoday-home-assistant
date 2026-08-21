"""Somtoday integration exceptions."""


class SomtodayError(Exception):
    """Base error for Somtoday requests."""


class SomtodayAuthenticationError(SomtodayError):
    """Somtoday rejected the supplied credentials."""


class SomtodayConnectionError(SomtodayError):
    """Somtoday could not be reached or returned an invalid response."""
