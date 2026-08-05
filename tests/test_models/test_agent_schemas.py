import pytest
from pydantic import ValidationError

from src.models import AgentResult, Category, Severity


def valid_agent_payload(**overrides):
    payload = {
        "category": Category.WATER,
        "severity": Severity.HIGH,
        "summary": "Phat hien duong ong nuoc bi vo tai hanh lang tang 5.",
        "confidence": 0.93,
    }
    payload.update(overrides)
    return payload


def test_valid_complete_agent_result():
    result = AgentResult(
        category=Category.WATER,
        severity=Severity.HIGH,
        summary="Phat hien duong ong nuoc bi vo tai hanh lang tang 5.",
        red_flags=["water_leak", "slip_hazard"],
        text_categories=[Category.WATER, Category.INFRASTRUCTURE],
        image_category=Category.WATER,
        confidence=0.93,
        recommended_department="maintenance",
    )

    assert result.category is Category.WATER
    assert result.severity is Severity.HIGH
    assert result.summary == "Phat hien duong ong nuoc bi vo tai hanh lang tang 5."
    assert result.red_flags == ["water_leak", "slip_hazard"]
    assert result.text_categories == [Category.WATER, Category.INFRASTRUCTURE]
    assert result.image_category is Category.WATER
    assert result.confidence == 0.93
    assert result.recommended_department == "maintenance"


def test_valid_minimal_agent_result_uses_defaults():
    result = AgentResult(
        category=Category.ELECTRICITY,
        severity=Severity.MEDIUM,
        summary="Tu dien phat ra am thanh bat thuong.",
        confidence=0.75,
    )

    assert result.category is Category.ELECTRICITY
    assert result.severity is Severity.MEDIUM
    assert result.summary == "Tu dien phat ra am thanh bat thuong."
    assert result.confidence == 0.75
    assert result.red_flags == []
    assert result.text_categories == []
    assert result.image_category is None
    assert result.recommended_department is None


def test_agent_result_converts_raw_enum_strings():
    result = AgentResult(
        category="water",
        severity="high",
        summary="Water leak near the hallway.",
        confidence=0.9,
    )

    assert result.category is Category.WATER
    assert result.severity is Severity.HIGH


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_agent_result_accepts_confidence_boundaries(confidence):
    result = AgentResult(**valid_agent_payload(confidence=confidence))

    assert result.confidence == confidence


@pytest.mark.parametrize(
    "override",
    [
        {"category": "plumbing"},
        {"severity": "urgent"},
        {"summary": "abcd"},
        {"summary": "a" * 501},
        {"confidence": -0.01},
        {"confidence": 1.01},
        {"unknown_field": "invalid"},
        {"recommended_department": "a" * 101},
    ],
)
def test_agent_result_rejects_invalid_values(override):
    with pytest.raises(ValidationError):
        AgentResult(**valid_agent_payload(**override))


@pytest.mark.parametrize(
    "missing_field",
    [
        "category",
        "severity",
        "summary",
        "confidence",
    ],
)
def test_agent_result_requires_mandatory_fields(missing_field):
    payload = valid_agent_payload()
    del payload[missing_field]

    with pytest.raises(ValidationError):
        AgentResult(**payload)


def test_agent_result_default_lists_are_not_shared():
    first = AgentResult(**valid_agent_payload())
    second = AgentResult(**valid_agent_payload())

    first.red_flags.append("water_leak")
    first.text_categories.append(Category.WATER)

    assert second.red_flags == []
    assert second.text_categories == []


def test_agent_result_serializes_enums_to_json_values():
    result = AgentResult(**valid_agent_payload())

    dumped = result.model_dump(mode="json")

    assert dumped["category"] == "water"
    assert dumped["severity"] == "high"
