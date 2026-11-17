import io

import pytest
from conftest import reply

from omnibus import load_persona
from omnibus.cli import CUT_SHORT, DECLINED, FAREWELL, GREETING, NO_KEY, TERMINAL, main


@pytest.fixture(autouse=True)
def no_env_file(monkeypatch):
    """Keep a developer's real .env out of the tests."""
    monkeypatch.setattr("omnibus.cli.load_dotenv", lambda: None)


def sitting(client, *typed, args=()):
    """Run the terminal with scripted typing. Returns the exit code and everything printed."""
    lines = iter(typed)

    def read(prompt):
        try:
            return next(lines)
        except StopIteration:
            raise EOFError from None

    out = io.StringIO()
    code = main(list(args), client=client, read=read, out=out)
    return code, out.getvalue()


def test_a_sitting_from_greeting_to_farewell(fake_client):
    client = fake_client(reply("Good ", "morrow!"))
    code, printed = sitting(client, "Hello, Omnibus.", "/quit")
    assert code == 0
    assert printed.startswith(GREETING)
    assert "Omnibus: Good morrow!" in printed
    assert printed.rstrip().endswith(FAREWELL)


def test_the_cost_line_follows_each_reply(fake_client):
    _, printed = sitting(fake_client(reply("Certainly.")), "Hello.", "/quit")
    assert "[claude-fable-5-2: 120 tokens in, 40 out, about $" in printed


def test_quiet_hides_the_cost_line(fake_client):
    _, printed = sitting(fake_client(reply("Certainly.")), "Hello.", "/quit", args=["--quiet"])
    assert "tokens in" not in printed


def test_an_empty_line_sends_nothing(fake_client):
    client = fake_client(reply("Certainly."))
    sitting(client, "", "   ", "Hello.", "/quit")
    assert len(client.calls) == 1


def test_the_end_of_input_ends_the_sitting_politely(fake_client):
    code, printed = sitting(fake_client())
    assert code == 0
    assert printed.rstrip().endswith(FAREWELL)


def test_the_chosen_model_and_effort_reach_the_request(fake_client):
    client = fake_client(reply("Certainly.", model="claude-haiku-5-5"))
    sitting(client, "Hello.", "/quit", args=["--model", "claude-haiku-5-5", "--effort", "low"])
    assert client.calls[0]["model"] == "claude-haiku-5-5"
    assert client.calls[0]["output_config"] == {"effort": "low"}


def test_the_terminal_asks_for_plain_text(fake_client):
    # In the first live sitting, **bold** arrived as asterisks: a terminal shows symbols as typed.
    client = fake_client(reply("Certainly."))
    sitting(client, "Hello.", "/quit")
    system = client.calls[0]["system"]
    assert system.startswith(load_persona())
    assert system.endswith(TERMINAL)
    assert "no Markdown" in TERMINAL


def test_a_declined_request_is_explained(fake_client):
    client = fake_client(reply(stop_reason="refusal", content=[]))
    _, printed = sitting(client, "Something Claude declines.", "/quit")
    assert DECLINED in printed


def test_a_reply_cut_short_is_explained(fake_client):
    client = fake_client(reply("Once upon a", stop_reason="max_tokens"))
    _, printed = sitting(client, "A very long tale, please.", "/quit")
    assert CUT_SHORT in printed


def test_a_missing_key_gives_plain_instructions(fake_client):
    # This is the error the SDK raises, before any request, when it finds no key.
    missing = TypeError("Could not resolve authentication method. Expected one of api_key, ...")
    code, printed = sitting(fake_client(reply(error=missing)), "Hello.")
    assert code == 2
    assert NO_KEY in printed


def test_any_other_type_error_is_not_swallowed(fake_client):
    client = fake_client(reply(error=TypeError("a real bug")))
    with pytest.raises(TypeError, match="a real bug"):
        sitting(client, "Hello.")
