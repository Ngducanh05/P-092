import pytest
from pydantic import ValidationError

from src.models.agent_schemas import AgentAnalyzeRequest, AgentResult


def test_agent_contract_contains_only_ai_outputs():
    result = AgentResult(
        text_categories=["WATER_LEAK"],
        red_flag_text=False,
        image_categories=["WATER_LEAK"],
        red_flag_signal=False,
        severity="MEDIUM",
        severity_source="VISION",
        text_model_version="model-text-v1",
        vision_model_version="model-vision-v1",
    )
    assert result.severity.value == "MEDIUM"
    dumped = result.model_dump()
    for backend_owned in ("priority", "score_total", "category_match", "ceiling_applied"):
        assert backend_owned not in dumped


def test_agent_contract_forbids_backend_owned_fields():
    with pytest.raises(ValidationError):
        AgentResult(
            text_categories=["WATER_LEAK"], red_flag_text=False, image_categories=None,
            red_flag_signal=False, severity="LOW", severity_source="TEXT_FALLBACK",
            text_model_version="v1", priority="P3"
        )


def test_agent_analyze_request_matches_self_dev_boundary():
    payload = AgentAnalyzeRequest.model_validate(
        {
            "ticket_id": "11111111-1111-4111-8111-111111111111",
            "text": "Có mùi khét ở ổ cắm",
            "image": {
                "storage_bucket": "ticket-attachments",
                "object_path": "tickets/u/2026/08/example.jpg",
            },
            "rule_version_id": "22222222-2222-4222-8222-222222222222",
        }
    )
    assert str(payload.ticket_id) == "11111111-1111-4111-8111-111111111111"
    assert payload.image is not None
    assert payload.image.storage_bucket == "ticket-attachments"
