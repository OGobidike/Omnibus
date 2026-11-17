"""Omnibus's side of the conversation: what is sent to Claude, and what is remembered."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from omnibus.persona import load_persona

DEFAULT_MODEL = "claude-fable-5-2"
DEFAULT_EFFORT = "medium"
EFFORTS = ("low", "medium", "high", "xhigh", "max")

# The most one reply may cost in output tokens. Thinking counts as output too.
DEFAULT_MAX_TOKENS = 16_000

# When one of these models declines a request, the API can run it again on another model
# inside the same call. Claude Haiku 5.5 has no such fallback, so it is not listed.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MODELS_WITH_FALLBACK = frozenset({"claude-fable-5-2", "claude-opus-5-5", "claude-sonnet-5-5"})

# After a fallback, these blocks from the model that declined must not be sent back.
_DROPPED_BEFORE_FALLBACK = frozenset({"thinking", "redacted_thinking", "tool_use"})


@dataclass(frozen=True)
class Turn:
    """What came back from one reply."""

    text: str
    model: str
    stop_reason: str | None
    usage: Any
    refused: bool = False


def blocks_to_send_back(content: Iterable[Any]) -> list[Any]:
    """Choose which blocks of a reply go into the history for the next request.

    Normally that is every block, unchanged: Claude expects its own thinking blocks back
    exactly as it wrote them. The exception is a reply that fell back to another model part
    of the way through. The API marks the switch with a "fallback" block, and the first
    model's thinking before that block must be left out, while the fallback block itself
    stays where it was.
    """
    blocks = list(content)
    switches = [index for index, block in enumerate(blocks) if block.type == "fallback"]
    if not switches:
        return blocks
    last_switch = switches[-1]
    return [
        block
        for index, block in enumerate(blocks)
        if index >= last_switch or block.type not in _DROPPED_BEFORE_FALLBACK
    ]


class Omnibus:
    """One sitting with Omnibus. It keeps the whole conversation, because the API keeps none."""

    def __init__(
        self,
        client: Any,
        *,
        model: str = DEFAULT_MODEL,
        effort: str = DEFAULT_EFFORT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        persona: str | None = None,
        setting: str | None = None,
    ) -> None:
        if effort not in EFFORTS:
            raise ValueError(f"effort must be one of {', '.join(EFFORTS)}; got {effort!r}")
        self.client = client
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self.persona = load_persona() if persona is None else persona
        # The setting says where this sitting takes place (a terminal, a web page). It follows
        # the character and is kept apart from it, so the character file stays the same
        # wherever Omnibus speaks.
        self.system = self.persona if setting is None else f"{self.persona}\n{setting}"
        self.history: list[dict[str, Any]] = []
        self.last_turn: Turn | None = None

    def say(self, words: str) -> Iterator[str]:
        """Send The Wanderer's words and yield Omnibus's reply as it is written.

        The exchange joins the history only once the reply has arrived whole. If the request
        fails, or Claude declines it, the history is left as it was, so the sitting can go on.
        """
        messages = [*self.history, {"role": "user", "content": words}]
        open_stream, request = self._request(messages)
        with open_stream(**request) as stream:
            yield from stream.text_stream
            reply = stream.get_final_message()

        refused = reply.stop_reason == "refusal"
        self.last_turn = Turn(
            text="".join(block.text for block in reply.content if block.type == "text"),
            model=reply.model,
            stop_reason=reply.stop_reason,
            usage=reply.usage,
            refused=refused,
        )
        if not refused:
            answer = {"role": "assistant", "content": blocks_to_send_back(reply.content)}
            self.history = [*messages, answer]

    def _request(self, messages: list[dict[str, Any]]) -> tuple[Any, dict[str, Any]]:
        """Build one request. Returns the SDK method to call and its arguments."""
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.system,
            "messages": messages,
            # Claude decides when to think; effort sets how hard it works.
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self.effort},
            # Re-read the unchanged start of the prompt (the character, then the history so
            # far) from the cache.
            "cache_control": {"type": "ephemeral"},
        }
        if self.model in MODELS_WITH_FALLBACK:
            request["betas"] = [FALLBACK_BETA]
            request["fallbacks"] = "default"
            return self.client.beta.messages.stream, request
        return self.client.messages.stream, request
