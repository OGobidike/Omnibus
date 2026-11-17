import pytest
from conftest import fallback_block, reply, text_block, thinking_block

from omnibus import Omnibus, load_persona
from omnibus.companion import FALLBACK_BETA, blocks_to_send_back


def hear(omnibus, words):
    """Collect a whole reply, the way the terminal does."""
    return "".join(omnibus.say(words))


def test_the_reply_streams_out_in_pieces(fake_client):
    omnibus = Omnibus(fake_client(reply("Good ", "morrow, ", "Wanderer!")))
    pieces = list(omnibus.say("Hello, Omnibus."))
    assert pieces == ["Good ", "morrow, ", "Wanderer!"]
    assert omnibus.last_turn.text == "Good morrow, Wanderer!"


def test_the_first_request_carries_the_character_and_ends_with_the_user(fake_client):
    client = fake_client(reply("At your service."))
    hear(Omnibus(client), "Hello, Omnibus.")
    request = client.calls[0]
    assert request["system"] == load_persona()
    assert request["messages"] == [{"role": "user", "content": "Hello, Omnibus."}]
    assert request["thinking"] == {"type": "adaptive"}
    assert request["output_config"] == {"effort": "medium"}
    assert request["cache_control"] == {"type": "ephemeral"}


def test_a_setting_follows_the_character_and_leaves_it_whole(fake_client):
    client = fake_client(reply("At your service."))
    hear(Omnibus(client, setting="## This sitting\n\nA lantern-lit inn."), "Hello.")
    system = client.calls[0]["system"]
    assert system.startswith(load_persona())
    assert system.endswith("A lantern-lit inn.")


def test_the_whole_conversation_is_sent_each_time(fake_client):
    # In 2024 every question arrived alone. Now each request holds everything said so far.
    client = fake_client(reply("Rome was not built in a day."), reply("Nor in two."))
    omnibus = Omnibus(client)
    hear(omnibus, "Tell me of Rome.")
    hear(omnibus, "And in two days?")
    second = client.calls[1]["messages"]
    assert [message["role"] for message in second] == ["user", "assistant", "user"]
    assert second[0]["content"] == "Tell me of Rome."
    assert second[2]["content"] == "And in two days?"


def test_thinking_blocks_go_back_unchanged(fake_client):
    client = fake_client(reply("One."), reply("Two."))
    omnibus = Omnibus(client)
    hear(omnibus, "First.")
    hear(omnibus, "Second.")
    sent_back = client.calls[1]["messages"][1]["content"]
    assert [block.type for block in sent_back] == ["thinking", "text"]


def test_no_sampling_settings_are_sent(fake_client):
    # The 2024 code set temperature. Current Claude models reject it.
    client = fake_client(reply("Certainly."))
    hear(Omnibus(client), "Hello.")
    assert {"temperature", "top_p", "top_k"}.isdisjoint(client.calls[0])


def test_models_with_a_fallback_ask_for_it(fake_client):
    client = fake_client(reply("Certainly."))
    hear(Omnibus(client, model="claude-fable-5-2"), "Hello.")
    request = client.calls[0]
    assert request["endpoint"] == "beta.messages"
    assert request["betas"] == [FALLBACK_BETA]
    assert request["fallbacks"] == "default"


def test_haiku_is_sent_without_a_fallback(fake_client):
    client = fake_client(reply("Certainly.", model="claude-haiku-5-5"))
    hear(Omnibus(client, model="claude-haiku-5-5"), "Hello.")
    request = client.calls[0]
    assert request["endpoint"] == "messages"
    assert "fallbacks" not in request
    assert "betas" not in request


def test_a_declined_request_leaves_the_conversation_as_it_was(fake_client):
    client = fake_client(
        reply("Rome was not built in a day."),
        reply(stop_reason="refusal", content=[]),
        reply("Gladly."),
    )
    omnibus = Omnibus(client)
    hear(omnibus, "Tell me of Rome.")
    before = list(omnibus.history)
    hear(omnibus, "Something Claude declines.")
    assert omnibus.last_turn.refused
    assert omnibus.history == before
    hear(omnibus, "Then tell me of Carthage.")
    assert [m["content"] for m in client.calls[2]["messages"] if m["role"] == "user"] == [
        "Tell me of Rome.",
        "Then tell me of Carthage.",
    ]


def test_a_failed_request_leaves_the_conversation_as_it_was(fake_client):
    client = fake_client(reply("Half a rep", error=ConnectionError("the line dropped")))
    omnibus = Omnibus(client)
    with pytest.raises(ConnectionError):
        hear(omnibus, "Hello.")
    assert omnibus.history == []
    assert omnibus.last_turn is None


def test_an_unknown_effort_is_refused_before_any_request(fake_client):
    with pytest.raises(ValueError, match="effort must be one of"):
        Omnibus(fake_client(), effort="heroic")


def test_every_block_is_sent_back_when_no_model_stepped_in():
    content = [thinking_block(), text_block("A tale.")]
    assert blocks_to_send_back(content) == content


def test_after_a_fallback_the_first_models_thinking_is_left_out():
    first_thought, first_words = thinking_block("one"), text_block("Once upon")
    switch = fallback_block()
    second_thought, second_words = thinking_block("two"), text_block(" a time.")
    content = [first_thought, first_words, switch, second_thought, second_words]
    assert blocks_to_send_back(content) == [first_words, switch, second_thought, second_words]
