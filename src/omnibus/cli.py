"""The terminal: a sitting with Omnibus, typed and read."""

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import Any, TextIO

import anthropic
from dotenv import load_dotenv

from omnibus.companion import DEFAULT_EFFORT, DEFAULT_MAX_TOKENS, DEFAULT_MODEL, EFFORTS, Omnibus
from omnibus.pricing import usage_line

GREETING = "Omnibus, at your service. Type your words and press Enter. /quit ends the sitting."
FAREWELL = "Safe travels, Wanderer."
NO_KEY = (
    "Omnibus needs a Claude API key to speak.\n"
    "Copy .env.example to .env and paste your key into it, or set ANTHROPIC_API_KEY.\n"
    "Keys are made at https://platform.claude.com/settings/keys"
)
DECLINED = (
    "(Claude declined that request, so it was left out of the conversation. Try other words.)"
)
# Sent after the character, so Omnibus writes for a screen that shows symbols as typed.
TERMINAL = """\
## This sitting

You are speaking in a plain text terminal, which shows every symbol exactly as typed. Write \
plain text only: no Markdown, so no asterisks for bold, no # headings and no tables. Give your \
answer shape with blank lines, short paragraphs, simple numbered lists and hyphens.
"""
CUT_SHORT = (
    "(That reply reached its length limit and was cut short. --max-tokens raises the limit.)"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omnibus",
        description="Talk with Omnibus, a polite storytelling companion built on Claude.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="the Claude model that plays Omnibus (default: %(default)s)",
    )
    parser.add_argument(
        "--effort",
        choices=EFFORTS,
        default=DEFAULT_EFFORT,
        help="how hard the model works on each reply (default: %(default)s)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="the longest one reply may be, thinking included (default: %(default)s)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="hide the line of tokens and cost after each reply",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    client: Any = None,
    read: Callable[[str], str] = input,
    out: TextIO | None = None,
) -> int:
    """Run one sitting. Returns the exit code: 0 for a normal end, 2 when no key was found."""
    out = sys.stdout if out is None else out
    args = build_parser().parse_args(argv)
    load_dotenv()
    if client is None:
        client = anthropic.Anthropic()
    omnibus = Omnibus(
        client,
        model=args.model,
        effort=args.effort,
        max_tokens=args.max_tokens,
        setting=TERMINAL,
    )

    print(GREETING, file=out)
    while True:
        try:
            words = read("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(file=out)
            break
        if words in {"/quit", "/exit"}:
            break
        if not words:
            continue

        print("\nOmnibus: ", end="", file=out, flush=True)
        try:
            for text in omnibus.say(words):
                print(text, end="", file=out, flush=True)
        except TypeError as error:
            # The SDK raises this before any request when it finds no key at all.
            if "authentication" not in str(error):
                raise
            print(f"\n{NO_KEY}", file=out)
            return 2
        except anthropic.AuthenticationError:
            print(f"\nClaude did not accept the API key.\n{NO_KEY}", file=out)
            return 2
        except anthropic.APIConnectionError:
            print("\n(Could not reach Claude. Check the connection and try again.)", file=out)
            continue
        except anthropic.APIStatusError as error:
            # Rate limits, a reached spend limit, an unknown model name, a server fault.
            print(f"\n(Claude answered with an error: {error.message})", file=out)
            continue
        print(file=out)

        turn = omnibus.last_turn
        if turn.refused:
            print(DECLINED, file=out)
        elif turn.stop_reason == "max_tokens":
            print(CUT_SHORT, file=out)
        if not args.quiet:
            print(usage_line(turn.model, turn.usage), file=out)

    print(FAREWELL, file=out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
