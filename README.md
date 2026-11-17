# 🤖 Omnibus

Omnibus is a polite storytelling robot you talk with in your terminal. He tells history, works sums and spins tall tales, and he has one firm rule: **a tall tale is never passed off as history.**

I made him for two kinds of people:

- **Anyone who likes a good story.** He explains things plainly, with manners and a little comedy, and he tells you which parts of a story are true.
- **Anyone learning to build with Claude.** This repo is a small, complete example you can read in one sitting: about 300 lines of Python, with tests that run without an API key.

## ✨ What he does today

| | |
|---|---|
| **Remembers the conversation** | Every request carries everything said so far, so he can follow a thread. |
| **Speaks as he writes** | Replies stream into the terminal piece by piece. |
| **Has a character you can read** | His whole personality is one prose file, [`persona.md`](src/omnibus/persona.md). Change the file and you change him. |
| **Keeps tales and history apart** | He says which parts of a story are record and which he made up. This is a rule in his character file. I haven't measured how well he keeps it yet; that test is next on my list. |
| **Shows what each reply cost** | A line after every reply gives the tokens used and an estimate in dollars. |
| **Fails politely** | A declined request, a dropped connection or a missing key each get a plain message, and the conversation carries on where it can. |

## 🚀 Try it

You need [uv](https://docs.astral.sh/uv/) and a [Claude API key](https://platform.claude.com/settings/keys).

```bash
git clone https://github.com/OGobidike/Omnibus.git
cd Omnibus
uv sync
cp .env.example .env
```

Paste your key into `.env`, then:

```bash
uv run omnibus
```

Type your words and press Enter. `/quit` ends the sitting.

**Each reply costs real money**, charged to your key. By default Omnibus is played by Claude Fable 5.2, Anthropic's most capable model. To meet him for a fraction of the price:

```bash
uv run omnibus --model claude-haiku-5-5
```

`uv run omnibus --help` lists the other settings.

## ✅ Tested

- ✅ **42 tests**, run by CI on every push and pull request
- ✅ **No test needs a key, touches the network or costs anything.** A fixture fails any test that tries to connect.
- ✅ **Two kinds of stand-in.** Most tests replace the Anthropic SDK with a simple fake. The rest keep the real SDK and replace only the network under it, so they check exactly what goes over the wire.
- ✅ `ruff check` and `ruff format --check` pass

Run them yourself:

```bash
uv run pytest
```

## 🧱 How it is built

| File | What it holds |
|---|---|
| [`src/omnibus/persona.md`](src/omnibus/persona.md) | His character, as prose |
| [`src/omnibus/companion.py`](src/omnibus/companion.py) | The conversation: what is sent to Claude, and what is remembered |
| [`src/omnibus/cli.py`](src/omnibus/cli.py) | The terminal |
| [`src/omnibus/pricing.py`](src/omnibus/pricing.py) | The cost line |
| [`tests/`](tests) | The tests and the stand-ins for Claude |

A few choices worth knowing about:

- **Claude's API keeps no memory**, so Omnibus keeps the conversation himself and sends all of it with every request.
- **The character comes first and never changes.** An unchanged start of a request can be re-read from Claude's prompt cache at a fraction of the price, so the request marks it for caching.
- **Claude's thinking goes back exactly as it came.** The API expects each thinking block returned unchanged on the next request, so the history stores whole replies, not only their text.
- **There is no `temperature` setting.** Current Claude models reject it. The dial that remains is `--effort`, which sets how hard the model works on a reply.
- **A declined request is not the end.** Claude's safety checks can decline a request. Omnibus asks the API to try a second model when that happens, and if the request is still declined, he leaves it out of the conversation and carries on.

## 🗺️ What comes next

- **Sources he can show.** History answers will carry links to where the facts came from.
- **A calculator he must use.** Sums will be computed, never guessed.
- **A memory between sittings**, kept in plain files you can read and delete.
- **A test sheet** that measures his manners and his honesty, with every number rebuilt by one command.
- **A seat in [the CBC](https://github.com/OGobidike/The-CBC-ChatBotCongress)**, my Chatbot Congress, the debating chamber I am rebuilding next.

---

Omnibus began in 2024 as a 38-line script. That version is kept at the [`v2024` tag](https://github.com/OGobidike/Omnibus/tree/v2024).
