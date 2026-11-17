import pytest
from conftest import usage

from omnibus.pricing import PRICES, estimate_cost, usage_line


def test_cost_adds_up_each_kind_of_token():
    # 1,000 in at $8, 500 out at $40, 2,000 written to cache at $10, 4,000 read at $0.20,
    # all per million tokens.
    spent = usage(input_tokens=1_000, output_tokens=500, cache_write=2_000, cache_read=4_000)
    expected = (1_000 * 8 + 500 * 40 + 2_000 * 10 + 4_000 * 0.20) / 1_000_000
    assert estimate_cost("claude-fable-5-2", spent) == pytest.approx(expected)


def test_an_unlisted_model_gets_no_dollar_figure():
    assert estimate_cost("some-future-model", usage()) is None
    assert "$" not in usage_line("some-future-model", usage())


def test_the_line_shows_tokens_and_an_estimate():
    line = usage_line("claude-haiku-5-5", usage(input_tokens=1_204, output_tokens=312))
    assert line == "[claude-haiku-5-5: 1,204 tokens in, 312 out, about $0.0003]"


def test_tokens_in_counts_everything_claude_read():
    # The first live sitting printed "4 tokens in" for a 2,879-token request, because the API
    # reports the cached part of the input separately.
    first = usage(input_tokens=4, output_tokens=127, cache_write=2_875)
    line = usage_line("claude-haiku-5-5", first)
    assert line.startswith("[claude-haiku-5-5: 2,879 tokens in (2,875 written to cache), 127 out")


def test_cache_reads_and_writes_are_both_shown():
    later = usage(input_tokens=4, output_tokens=594, cache_write=150, cache_read=2_882)
    line = usage_line("claude-fable-5-2", later)
    assert "3,036 tokens in (2,882 read from cache, 150 written to cache), 594 out" in line


def test_a_missing_count_is_treated_as_zero():
    # Some counts come back as None when they don't apply.
    spent = usage()
    spent.cache_read_input_tokens = None
    assert estimate_cost("claude-opus-5-5", spent) is not None


def test_cache_reads_cost_less_than_fresh_input():
    for price in PRICES.values():
        assert price.cache_read < price.input < price.output
