"""Cascade resolution tests — the per-field fill-the-gap merge primitive and the
recursive `resolve_llm_cascade` walk over the static call tree."""

from agent_composer.llm_clients.config import merge_llm_config


def test_merge_specific_wins_per_field():
    specific = {"model": "claude-opus-4-8"}
    base = {"provider": "anthropic", "model": "claude-sonnet-4-5", "temperature": 0.2}
    # specific wins per field; base fills the gaps (provider, temperature)
    assert merge_llm_config(specific, base) == {
        "provider": "anthropic",
        "model": "claude-opus-4-8",
        "temperature": 0.2,
    }


def test_merge_empty_layers():
    assert merge_llm_config({}, {}) == {}
    assert merge_llm_config({"model": "x"}, {}) == {"model": "x"}
    assert merge_llm_config({}, {"model": "y"}) == {"model": "y"}


def test_merge_does_not_mutate_inputs():
    a, b = {"model": "x"}, {"provider": "p"}
    merge_llm_config(a, b)
    assert a == {"model": "x"} and b == {"provider": "p"}
