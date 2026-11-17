"""Omnibus: a polite storytelling companion built on Claude."""

from omnibus.companion import DEFAULT_EFFORT, DEFAULT_MODEL, Omnibus, Turn
from omnibus.persona import load_persona

__version__ = "0.1.0"

__all__ = ["DEFAULT_EFFORT", "DEFAULT_MODEL", "Omnibus", "Turn", "__version__", "load_persona"]
