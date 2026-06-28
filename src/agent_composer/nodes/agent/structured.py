"""Structured AGENT output — derive a pydantic schema from a declared `output:` Shape and
generate a value that conforms to it.

An AGENT declares `output:` as a typed `Shape`. For a bare `str` (or a `Literal[...]`
variant) the agent stays a text producer — `shape_to_schema` returns `None` and the mode
takes the plain-text path. For any richer shape (a record, a scalar `int`/`float`/`bool`, a
list) `shape_to_schema` builds a `pydantic.BaseModel` the mode hands to
`with_structured_output`, so the model emits a value the engine's write boundary
(`pool.set(..., declared=output_shape)`) accepts.

Scalars and lists can't be a top-level pydantic model field on their own, so they are wrapped
in a single-field model (`{"value": <scalar>}` / `{"items": [<element>]}`); `_unwrap` strips
the wrapper back to the bare value after generation. A record maps one model field per
declared field and passes through as the dumped dict.

Layer: nodes — imports `state` (Shape/SegmentType) + `pydantic`; no engine/runtime imports.
"""

from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, create_model

from agent_composer.state.segments import Shape, SegmentType

# SegmentType -> python type for a scalar slot. DATE/DATETIME persist as ISO strings.
_SCALAR_PY: dict[SegmentType, type] = {
    SegmentType.STRING: str,
    SegmentType.INTEGER: int,
    SegmentType.NUMBER: float,
    SegmentType.BOOLEAN: bool,
    SegmentType.DATE: str,
    SegmentType.DATETIME: str,
}


def _py_type(shape: Shape) -> Any:
    """The python annotation for a value of `shape` as a pydantic field type.

    A `STRING` with `tags` is a `Literal[...]` variant; a nested `OBJECT` with `fields`
    becomes its own submodel; a `LIST_*` becomes `list[<element type>]`. Raises `ValueError`
    for a type with no structured mapping (`NONE`, `FILE`) so a new SegmentType is loud.
    """
    seg = shape.seg_type
    if seg == SegmentType.STRING and shape.tags:
        return Literal[tuple(sorted(shape.tags))]  # type: ignore[valid-type]
    if seg in _SCALAR_PY:
        return _SCALAR_PY[seg]
    if seg == SegmentType.OBJECT:
        return _record_model(shape) if shape.fields else dict
    if seg == SegmentType.LIST_ANY:
        return list
    if seg.is_list():
        elem = shape.element
        if elem is not None:
            return List[_py_type(elem)]  # type: ignore[misc]
        scalar = seg.element_type
        return List[_SCALAR_PY[scalar]] if scalar in _SCALAR_PY else list  # type: ignore[misc]
    raise ValueError(f"shape_to_schema: no structured mapping for segment type {seg!r}")


def _record_model(shape: Shape) -> type[BaseModel]:
    """Build a pydantic model from an `OBJECT` Shape: one field per `fields` entry, required
    iff named in `required` (others default to `None`); `nullable` widens a field to Optional."""
    required = shape.required or frozenset()
    spec: dict[str, Any] = {}
    for name, sub in (shape.fields or {}).items():
        ann = _py_type(sub)
        if name in required and not sub.nullable:
            spec[name] = (ann, ...)
        else:
            spec[name] = (Optional[ann], None)
    return create_model("Record", **spec)


def shape_to_schema(shape: Shape) -> Optional[type[BaseModel]]:
    """Derive a pydantic model for `shape`, or `None` when the agent should stay a text
    producer (a bare `str` or a `Literal[...]` variant — today's passthrough).

    A record (`OBJECT` with `fields`) maps directly to a model. A scalar or a list can't be a
    standalone model, so it is wrapped in a single-field model (`value` / `items`) that
    `_unwrap` later strips.
    """
    seg = shape.seg_type
    if seg == SegmentType.STRING:
        return None  # bare str OR a Literal variant — keep the text path
    if seg == SegmentType.OBJECT and shape.fields:
        return _record_model(shape)
    if seg.is_list() or seg == SegmentType.LIST_ANY:
        return create_model("ListWrapper", items=(_py_type(shape), ...))
    # any other scalar (int/float/bool/date/datetime) or freeform object -> value wrapper
    return create_model("ScalarWrapper", value=(_py_type(shape), ...))


def _unwrap(obj: BaseModel, shape: Shape) -> Any:
    """Strip the single-field wrapper `shape_to_schema` adds for a scalar/list, returning the
    bare value the write boundary expects. A record is returned as its dumped dict."""
    data = obj.model_dump()
    seg = shape.seg_type
    if seg == SegmentType.OBJECT and shape.fields:
        return data
    if seg.is_list() or seg == SegmentType.LIST_ANY:
        return data["items"]
    return data["value"]
