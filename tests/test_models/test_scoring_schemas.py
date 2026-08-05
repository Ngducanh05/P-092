import pytest
from pydantic import ValidationError

from src.models import Priority, ScoringResult


def valid_scoring_payload(**overrides):
    payload = {
        "severity_score": 35,
        "red_flag_score": 20,
        "impact_score": 10,
        "density_score": 5,
        "age_score": 5,
        "total_score": 75,
        "priority": Priority.P2,
    }
    payload.update(overrides)
    return payload


def test_valid_scoring_result():
    result = ScoringResult(
        severity_score=35,
        red_flag_score=20,
        impact_score=10,
        density_score=5,
        age_score=5,
        total_score=75,
        priority=Priority.P2,
        scoring_reasons=[
            "High severity",
            "Safety signal detected",
        ],
    )

    assert result.severity_score == 35
    assert result.red_flag_score == 20
    assert result.impact_score == 10
    assert result.density_score == 5
    assert result.age_score == 5
    assert result.total_score == 75
    assert result.priority is Priority.P2
    assert result.scoring_reasons == [
        "High severity",
        "Safety signal detected",
    ]


def test_scoring_result_accepts_minimum_boundaries():
    result = ScoringResult(
        severity_score=0,
        red_flag_score=0,
        impact_score=0,
        density_score=0,
        age_score=0,
        total_score=0,
        priority=Priority.P4,
    )

    assert result.total_score == 0
    assert result.priority is Priority.P4


def test_scoring_result_accepts_maximum_boundaries():
    result = ScoringResult(
        severity_score=40,
        red_flag_score=30,
        impact_score=15,
        density_score=10,
        age_score=5,
        total_score=100,
        priority=Priority.P1,
    )

    assert result.total_score == 100
    assert result.priority is Priority.P1


def test_scoring_result_converts_raw_priority_string():
    result = ScoringResult(**valid_scoring_payload(priority="p2"))

    assert result.priority is Priority.P2


def test_scoring_result_accepts_total_with_small_floating_point_tolerance():
    result = ScoringResult(
        severity_score=0.1,
        red_flag_score=0.2,
        impact_score=0.3,
        density_score=0.4,
        age_score=0.5,
        total_score=1.5,
        priority=Priority.P4,
    )

    assert result.total_score == 1.5


@pytest.mark.parametrize(
    "override",
    [
        {"severity_score": -0.01, "total_score": 39.99},
        {"severity_score": 40.01, "total_score": 80.01},
        {"red_flag_score": -0.01, "total_score": 54.99},
        {"red_flag_score": 30.01, "total_score": 105.01},
        {"impact_score": -0.01, "total_score": 64.99},
        {"impact_score": 15.01, "total_score": 80.01},
        {"density_score": -0.01, "total_score": 69.99},
        {"density_score": 10.01, "total_score": 80.01},
        {"age_score": -0.01, "total_score": 69.99},
        {"age_score": 5.01, "total_score": 75.01},
        {"total_score": -0.01},
        {"total_score": 100.01},
        {"priority": "urgent"},
        {"unknown_field": "invalid"},
        {"total_score": 90, "priority": Priority.P1},
    ],
)
def test_scoring_result_rejects_invalid_values(override):
    with pytest.raises(ValidationError):
        ScoringResult(**valid_scoring_payload(**override))


def test_scoring_result_requires_score_fields():
    payload = valid_scoring_payload()
    del payload["severity_score"]

    with pytest.raises(ValidationError):
        ScoringResult(**payload)


def test_scoring_result_default_lists_are_not_shared():
    first = ScoringResult(**valid_scoring_payload())
    second = ScoringResult(**valid_scoring_payload())

    first.scoring_reasons.append("High severity")

    assert second.scoring_reasons == []


def test_scoring_result_serializes_priority_to_json_value():
    result = ScoringResult(**valid_scoring_payload())

    dumped = result.model_dump(mode="json")

    assert dumped["priority"] == "p2"
