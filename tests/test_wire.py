"""The real Anthropic SDK, talking to a stand-in server.

The other tests replace the SDK with a simple fake. These keep the SDK and replace only the
network underneath it, so they check what truly goes over the wire and that a real streamed
reply is read correctly. Still no key, no network and no cost.
"""

import json

import anthropic
import httpx2
import pytest

from omnibus import Omnibus, load_persona


def event(name, data):
    return f"event: {name}\ndata: {json.dumps({'type': name, **data})}\n\n"


def streamed_reply(model, *pieces):
    """A reply in the API's streaming format: a thinking block, then text in pieces."""
    opening = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [],
        "stop_reason": None,
        "stop_sequence": None,
        "usage": {"input_tokens": 300, "output_tokens": 1},
    }
    thinking = {"type": "thinking", "thinking": "", "signature": ""}
    signed = {"type": "signature_delta", "signature": "signed-by-the-model"}
    events = [
        event("message_start", {"message": opening}),
        event("content_block_start", {"index": 0, "content_block": thinking}),
        event("content_block_delta", {"index": 0, "delta": signed}),
        event("content_block_stop", {"index": 0}),
        event("content_block_start", {"index": 1, "content_block": {"type": "text", "text": ""}}),
    ]
    for piece in pieces:
        delta = {"type": "text_delta", "text": piece}
        events.append(event("content_block_delta", {"index": 1, "delta": delta}))
    ending = {"stop_reason": "end_turn", "stop_sequence": None}
    events += [
        event("content_block_stop", {"index": 1}),
        event("message_delta", {"delta": ending, "usage": {"output_tokens": 42}}),
        event("message_stop", {}),
    ]
    return "".join(events)


class StandInServer:
    """Answers every request with the next scripted reply, and keeps what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        headers = {"content-type": "text/event-stream"}
        return httpx2.Response(200, headers=headers, text=self.replies.pop(0))

    def body(self, index):
        return json.loads(self.requests[index].content)

    def client(self):
        transport = httpx2.MockTransport(self)
        return anthropic.Anthropic(
            api_key="not-a-real-key",
            base_url="https://stand-in.invalid",
            http_client=httpx2.Client(transport=transport),
            max_retries=0,
        )


def test_a_streamed_reply_is_read_piece_by_piece():
    server = StandInServer(streamed_reply("claude-fable-5-2", "Good ", "morrow, ", "Wanderer!"))
    omnibus = Omnibus(server.client())
    assert list(omnibus.say("Hello, Omnibus.")) == ["Good ", "morrow, ", "Wanderer!"]
    turn = omnibus.last_turn
    assert turn.text == "Good morrow, Wanderer!"
    assert turn.stop_reason == "end_turn"
    assert (turn.usage.input_tokens, turn.usage.output_tokens) == (300, 42)


def test_what_goes_over_the_wire_for_fable():
    server = StandInServer(streamed_reply("claude-fable-5-2", "Certainly."))
    "".join(Omnibus(server.client()).say("Hello, Omnibus."))
    request, body = server.requests[0], server.body(0)
    assert request.url.path == "/v1/messages"
    assert "server-side-fallback-2026-07-01" in request.headers["anthropic-beta"]
    assert body["model"] == "claude-fable-5-2"
    assert body["fallbacks"] == "default"
    assert body["system"] == load_persona()
    assert body["messages"] == [{"role": "user", "content": "Hello, Omnibus."}]
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": "medium"}
    assert body["cache_control"] == {"type": "ephemeral"}
    assert body["stream"] is True
    assert {"temperature", "top_p", "top_k"}.isdisjoint(body)


def test_what_goes_over_the_wire_for_haiku():
    server = StandInServer(streamed_reply("claude-haiku-5-5", "Certainly."))
    "".join(Omnibus(server.client(), model="claude-haiku-5-5", effort="low").say("Hello."))
    request, body = server.requests[0], server.body(0)
    assert "fallbacks" not in body
    assert "server-side-fallback" not in request.headers.get("anthropic-beta", "")
    assert body["output_config"] == {"effort": "low"}


@pytest.mark.parametrize("model", ["claude-fable-5-2", "claude-haiku-5-5"])
def test_the_second_request_carries_the_first_exchange(model):
    server = StandInServer(
        streamed_reply(model, "Rome was not built in a day."),
        streamed_reply(model, "Nor in two."),
    )
    omnibus = Omnibus(server.client(), model=model)
    "".join(omnibus.say("Tell me of Rome."))
    "".join(omnibus.say("And in two days?"))
    first, answer, second = server.body(1)["messages"]
    assert first == {"role": "user", "content": "Tell me of Rome."}
    assert second == {"role": "user", "content": "And in two days?"}
    assert answer["role"] == "assistant"
    thought, words = answer["content"]
    # The thinking block returns exactly as the model signed it.
    assert (thought["type"], thought["signature"]) == ("thinking", "signed-by-the-model")
    assert (words["type"], words["text"]) == ("text", "Rome was not built in a day.")
