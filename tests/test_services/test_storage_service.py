"""Storage service tests."""

from uuid import uuid4

import pytest

from src.config import Settings
from src.models.api.errors import INVALID_ATTACHMENT, DomainError
from src.models.api.storage import SignedUploadRequest
from src.services.storage_service import StorageService


def test_path_generated_server_side_and_scoped_to_user():
    user_id = uuid4()
    service = StorageService(Settings(app_env="test"))

    path = service.generate_ticket_attachment_path(user_id, "leak.jpg", "image/jpeg")

    assert path.startswith(f"tickets/{user_id}/")
    assert path.endswith(".jpg")
    assert "leak.jpg" not in path


def test_rejects_svg_and_oversized_file():
    service = StorageService(Settings(app_env="test", max_ticket_image_bytes=10))

    with pytest.raises(DomainError) as svg_exc:
        service._validate_metadata(SignedUploadRequest(original_filename="x.svg", mime_type="image/svg+xml", file_size=1))
    assert svg_exc.value.code == INVALID_ATTACHMENT

    with pytest.raises(DomainError):
        service._validate_metadata(SignedUploadRequest(original_filename="x.jpg", mime_type="image/jpeg", file_size=11))


def test_rejects_path_traversal():
    service = StorageService(Settings(app_env="test"))

    with pytest.raises(DomainError):
        service.generate_ticket_attachment_path(uuid4(), "../x.jpg", "image/jpeg")
