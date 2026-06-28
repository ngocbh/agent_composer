"""HUMAN_INPUT — a structural gate that suspends the run for a person.

Deliver-as-Output model: on its single run the node ALWAYS emits
`PauseRequested(HumanInputRequired)` and parks. The host satisfies the pause with a
`DeliverAnswerCommand(node_id=this_node, value=answer)`; the engine writes that value
as the node's `Output` (`pool.set` + fire the out-edges) — the node never re-runs. Its
single output value is the delivered answer.
"""

from typing import Any, Optional

from agent_composer.expr.template import render_template_record
from agent_composer.nodes.base import Node, NodeKind, Pause
from agent_composer.suspension.pause import HumanInputRequired


class HumanInputNode(Node):
    """
    A structural gate that suspends the run for a person (deliver-as-Output model).

    On its single run the node always emits `Pause(HumanInputRequired)` and parks. The host
    satisfies it with a `DeliverAnswerCommand`, and the engine writes that answer as this node's
    Output — the node never re-runs.

    Args:
        node_id (`str`):
            The node's unique id.
        prompt (`str`):
            The text to show the human (rendered against the bound input record).
        answer_schema (`list[dict]`, *optional*, defaults to `None`):
            IOField-shaped description of the expected answer; defaults to `[]`.
        title (`str`, *optional*, defaults to `None`):
            Display title.
    """

    kind = NodeKind.HUMAN_INPUT

    def __init__(
        self,
        node_id: str,
        *,
        prompt: str,
        answer_schema: Optional[list[dict[str, Any]]] = None,
        title: Optional[str] = None,
    ) -> None:
        super().__init__(node_id, title=title)
        self.prompt = prompt
        self.answer_schema = answer_schema or []

    def run(self, inputs: dict):
        prompt = render_template_record(self.prompt, inputs)
        return Pause(
            HumanInputRequired(
                prompt=prompt,
                answer_schema=self.answer_schema,
                node_title=self.title,
                node_id=self.id,
            )
        )
