"""Stand-ins for Claude, so the tests need no key, no network and no money."""

import copy
import socket
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail any test that tries to open a network connection."""

    def refuse(*args, **kwargs):
        raise AssertionError("a test tried to reach the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def thinking_block(note=""):
    return SimpleNamespace(type="thinking", thinking=note, signature="sig")


def fallback_block():
    return SimpleNamespace(type="fallback")


def usage(input_tokens=120, output_tokens=40, cache_write=0, cache_read=0):
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_write,
        cache_read_input_tokens=cache_read,
    )


def reply(*chunks, model="claude-fable-5-2", stop_reason="end_turn", content=None, error=None):
    """Script one reply: the pieces of text that stream out, then the finished message."""
    if content is None:
        content = [thinking_block(), text_block("".join(chunks))]
    final = SimpleNamespace(content=content, model=model, stop_reason=stop_reason, usage=usage())
    return SimpleNamespace(chunks=chunks, final=final, error=error)


class FakeStream:
    """Behaves like the SDK's stream: a context manager with text_stream and a final message."""

    def __init__(self, scripted):
        self._scripted = scripted

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield from self._scripted.chunks
        if self._scripted.error is not None:
            raise self._scripted.error

    def get_final_message(self):
        return self._scripted.final


class FakeMessages:
    def __init__(self, script, calls, endpoint):
        self._script = script
        self._calls = calls
        self._endpoint = endpoint

    def stream(self, **request):
        # Copy the request: the history it points at keeps growing after this call.
        self._calls.append({"endpoint": self._endpoint, **copy.deepcopy(request)})
        return FakeStream(self._script.pop(0))


class FakeClient:
    """Plays back scripted replies and records every request it was sent."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []
        self.messages = FakeMessages(self.script, self.calls, "messages")
        self.beta = SimpleNamespace(messages=FakeMessages(self.script, self.calls, "beta.messages"))


@pytest.fixture
def fake_client():
    return FakeClient
