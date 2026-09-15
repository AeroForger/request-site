"""Expose the existing request API as a Vercel Python function."""

from server.app import application as app

__all__ = ["app"]
