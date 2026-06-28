"""`shape_to_schema` — derive a pydantic model from a declared output `Shape`."""

from agent_composer.state.segments import Shape, SegmentType
from agent_composer.nodes.agent.structured import shape_to_schema


def test_bare_str_returns_none():
    # scalar str stays today's text passthrough — no schema
    assert shape_to_schema(Shape.scalar(SegmentType.STRING)) is None


def test_variant_str_returns_none():
    # a Literal[...] variant stays text passthrough too (the model answers with one tag)
    shape = Shape(seg_type=SegmentType.STRING, tags=frozenset({"a", "b"}))
    assert shape_to_schema(shape) is None


def test_scalar_int_gets_schema():
    model = shape_to_schema(Shape.scalar(SegmentType.INTEGER))
    assert model is not None
    inst = model.model_validate({"value": 7})  # single-field wrapper named "value"
    assert inst.value == 7


def test_record_shape():
    shape = Shape(
        seg_type=SegmentType.OBJECT,
        fields={
            "name": Shape.scalar(SegmentType.STRING),
            "score": Shape.scalar(SegmentType.NUMBER),
        },
        required=frozenset({"name"}),
    )
    model = shape_to_schema(shape)
    inst = model.model_validate({"name": "a", "score": 1.5})
    assert inst.name == "a" and inst.score == 1.5


def test_list_of_records():
    elem = Shape(
        seg_type=SegmentType.OBJECT,
        fields={"x": Shape.scalar(SegmentType.INTEGER)},
        required=frozenset({"x"}),
    )
    shape = Shape(seg_type=SegmentType.LIST_OBJECT, element=elem)
    model = shape_to_schema(shape)
    inst = model.model_validate({"items": [{"x": 1}, {"x": 2}]})
    assert [i.x for i in inst.items] == [1, 2]
