"""Auth routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies.auth import CurrentActor, get_current_actor
from src.api.dependencies.database import get_db
from src.api.openapi_responses import AUTHENTICATED_RESPONSES
from src.models.api.auth import CurrentActorResponse
from src.repositories.unit_repository import UnitRepository
from src.services.auth_service import current_bql_response, current_resident_response, current_technician_response

router = APIRouter()

ME_RESPONSE_EXAMPLES = {
    "resident": {
        "summary": "Resident profile",
        "value": {
            "id": "11111111-1111-4111-8111-111111111111",
            "actor_type": "resident",
            "phone_number": "+84901234567",
            "full_name": "Nguyen Van A",
            "is_active": True,
            "active_unit_memberships": [
                {
                    "unit_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "building_code": "A",
                    "floor": "10",
                    "unit_number": "1002",
                    "is_active": True,
                }
            ],
        },
    },
    "bql": {
        "summary": "BQL staff profile",
        "value": {
            "id": "22222222-2222-4222-8222-222222222222",
            "actor_type": "bql",
            "email": "bql@example.invalid",
            "full_name": "BQL Staff",
            "is_active": True,
        },
    },
    "technician": {
        "summary": "Technician profile",
        "value": {
            "id": "33333333-3333-4333-8333-333333333333",
            "actor_type": "technician",
            "email": "tech@example.invalid",
            "full_name": "Nguyen Van Tech",
            "phone_number": "+84901234567",
            "is_active": True,
            "is_available": True,
        },
    },
}


@router.get(
    "/me",
    response_model=CurrentActorResponse,
    summary="Get current authenticated actor",
    description=(
        "Returns the Resident, BQL, or Technician profile for the Supabase Bearer access token. "
        "Residents receive active unit memberships. BQL staff receive only staff profile fields. "
        "Technicians receive their profile including availability status. "
        "Actor type is derived by the backend from profile tables, never from client-provided role metadata."
    ),
    operation_id="get_current_actor",
    responses={
        200: {
            "description": "Authenticated application profile.",
            "content": {"application/json": {"examples": ME_RESPONSE_EXAMPLES}},
        },
        **AUTHENTICATED_RESPONSES,
    },
)
def me(actor: CurrentActor = Depends(get_current_actor), db: Session = Depends(get_db)) -> CurrentActorResponse:
    if actor.actor_type == "resident":
        units = UnitRepository(db).list_active_memberships_for_resident(actor.profile.id)
        return current_resident_response(actor.profile, units)
    if actor.actor_type == "technician":
        return current_technician_response(actor.profile)  # type: ignore[arg-type]
    return current_bql_response(actor.profile)  # type: ignore[arg-type]
