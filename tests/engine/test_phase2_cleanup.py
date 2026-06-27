import importlib

import pytest


def test_update_variables_command_is_gone():
    cmds = importlib.import_module("agent_compose.suspension.commands")
    assert not hasattr(cmds, "UpdateVariablesCommand")
    assert not hasattr(cmds, "VariableUpdate")
    assert hasattr(cmds, "AbortCommand") and hasattr(cmds, "DeliverAnswerCommand")


def test_channels_module_is_gone():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("agent_compose.suspension.channels")


def test_effect_nodes_drop_scratch_keys():
    from agent_compose.nodes.human_input.node import HumanInputNode
    from agent_compose.nodes.wait.node import WaitNode

    hi = HumanInputNode("h", prompt="?")
    assert not hasattr(hi, "answer_key")
    w = WaitNode("w", is_timed=True)
    assert not hasattr(w, "release_key") and not hasattr(w, "payload_key")
