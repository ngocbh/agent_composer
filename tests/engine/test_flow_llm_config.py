"""Flow-level `llm_config:` — parsing it onto ComposeFile and threading it onto the
compiled flow (the cascade's flow layer)."""

from agent_composer.compose.parser import parse_file


def test_flow_level_llm_config_parsed():
    text = """
id: f
name: f
llm_config:
  provider: anthropic
  model: claude-sonnet-4-5
nodes:
  a:
    kind: agent
    prompt: hi
"""
    f = parse_file(text)
    assert f.llm_config == {"provider": "anthropic", "model": "claude-sonnet-4-5"}


def test_flow_level_llm_config_absent_is_empty():
    text = "id: f\nname: f\nnodes:\n  a:\n    kind: agent\n    prompt: hi\n"
    assert parse_file(text).llm_config == {}
