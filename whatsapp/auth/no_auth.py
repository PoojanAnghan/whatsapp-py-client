"""NoAuth — no session persistence. Mirrors src/authStrategies/NoAuth.js"""
from .base import BaseAuthStrategy


class NoAuth(BaseAuthStrategy):
    """Stateless auth: every run requires a fresh QR scan."""
    pass
