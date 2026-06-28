"""Resolve each AGENT node's effective `llm_config` by walking the static call tree.

Run ONCE at run start (the CLI layer is known only then). Fill-the-gap is per-field,
most-specific-wins, which is associative, so one top-down walk that accumulates the parent
config and bakes the effective dict onto every `AgentNode` is correct for arbitrary nesting.
Each CALL/MAP child is DEEP-COPIED before recursion so a shared/memoized def or external flow
is never mutated and two callsites with different parent configs stay isolated; runtime
expansion (`clone_child`) then deep-copies an already-resolved child, so the effective configs
ride into the live graph with no change to `expand.py`. On a DURABLE resume this must run
BEFORE `FlowEngine.restore` (restore's replay re-clones children from
`self.flow.nodes[spawner_id].child` — see `compose/run.py` / `runtime/engine.py`).

Layer: compile — imports nodes + compile.model only; never runtime.
"""

from __future__ import annotations

import copy

from agent_composer.llm_clients.config import merge_llm_config
from agent_composer.nodes.agent import AgentNode
from agent_composer.nodes.base import NodeKind


def resolve_llm_cascade(flow, parent_config: dict) -> None:
    """Bake the effective `llm_config` onto every `AgentNode` in `flow` and its baked
    children. `parent_config` is the accumulated fill-the-gap layer from the enclosing scope
    outward (the CLI config at the top call). Mutates `flow` in place.

    Args:
        flow: a `CompiledFlow` — its `flow_llm_config` is this scope's flow layer.
        parent_config (`dict`): the gap-fill layer inherited from outside this flow (the
            enclosing flow's resolved flow-layer; the CLI config at the top-level call).
    """
    # This flow's layer = its own flow-level config gap-filled by the parent chain.
    flow_layer = merge_llm_config(flow.flow_llm_config, parent_config)
    for node in flow.nodes.values():
        if isinstance(node, AgentNode):
            # Recompute from own_llm_config (the authored source) every pass — never from the
            # previously-baked effective dict — so re-resolution with a new layer is correct.
            node.llm_config = (
                dict(node.own_llm_config)
                if not node.llm_inherit
                else merge_llm_config(node.own_llm_config, flow_layer)
            )
        elif node.kind in (NodeKind.CALL, NodeKind.MAP) and getattr(node, "child", None) is not None:
            node.child = copy.deepcopy(node.child)  # per-callsite isolation
            resolve_llm_cascade(node.child, flow_layer)
