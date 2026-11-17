"""Omnibus's character lives in persona.md, beside this file, where it reads as plain prose."""

from importlib.resources import files


def load_persona() -> str:
    """Return the character file, exactly as written.

    The text is sent as the system prompt on every request. It must stay the same from one
    request to the next (no dates, no counters), because Claude re-reads an unchanged start of
    a prompt from its cache at a fraction of the price.
    """
    return files("omnibus").joinpath("persona.md").read_text(encoding="utf-8")
