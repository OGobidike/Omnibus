"""A rough cost for each reply, from Anthropic's list prices.

The token counts come from the API and are exact. The dollar figure is an estimate: prices
change, and a discount or a fallback to another model is not modelled. Claude Haiku 5.5 costs
more for prompts over 100,000 tokens, which is not modelled either.
"""

from dataclasses import dataclass
from typing import Any

# Read from https://platform.claude.com/docs/en/about-claude/pricing on this date.
PRICES_AS_OF = "2026-11-16"


@dataclass(frozen=True)
class Price:
    """US dollars per million tokens."""

    input: float
    output: float
    cache_write: float
    cache_read: float


PRICES = {
    "claude-fable-5-2": Price(input=8.00, output=40.00, cache_write=10.00, cache_read=0.20),
    "claude-opus-5-5": Price(input=4.00, output=20.00, cache_write=5.00, cache_read=0.20),
    "claude-sonnet-5-5": Price(input=2.00, output=10.00, cache_write=2.50, cache_read=0.10),
    "claude-haiku-5-5": Price(input=0.10, output=0.50, cache_write=0.125, cache_read=0.01),
}


def _count(usage: Any, name: str) -> int:
    return getattr(usage, name, None) or 0


def estimate_cost(model: str, usage: Any) -> float | None:
    """Return the estimated cost of one reply in US dollars, or None for an unlisted model."""
    price = PRICES.get(model)
    if price is None:
        return None
    return (
        _count(usage, "input_tokens") * price.input
        + _count(usage, "output_tokens") * price.output
        + _count(usage, "cache_creation_input_tokens") * price.cache_write
        + _count(usage, "cache_read_input_tokens") * price.cache_read
    ) / 1_000_000


def usage_line(model: str, usage: Any) -> str:
    """One line for the terminal: the tokens of a reply and, where known, about what it cost."""
    # The API reports input in three parts. Together they are everything Claude read.
    fresh = _count(usage, "input_tokens")
    written = _count(usage, "cache_creation_input_tokens")
    read = _count(usage, "cache_read_input_tokens")
    cache_notes = []
    if read:
        cache_notes.append(f"{read:,} read from cache")
    if written:
        cache_notes.append(f"{written:,} written to cache")
    tokens_in = f"{fresh + written + read:,} tokens in"
    if cache_notes:
        tokens_in += f" ({', '.join(cache_notes)})"
    parts = [tokens_in, f"{_count(usage, 'output_tokens'):,} out"]
    cost = estimate_cost(model, usage)
    if cost is not None:
        parts.append(f"about ${cost:.4f}")
    return f"[{model}: {', '.join(parts)}]"
