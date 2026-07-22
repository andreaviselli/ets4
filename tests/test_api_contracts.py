from __future__ import annotations

import pytest
from pydantic import ValidationError

from ets4.api.contracts import CreateReviewRequest


def test_create_review_requires_exactly_one_manuscript_source() -> None:
    by_url = CreateReviewRequest(
        manuscript_url="https://example.org/paper.pdf",
        model="gpt-5.6",
    )
    by_upload = CreateReviewRequest(upload_token="upload-123", model="gpt-5.6")

    assert str(by_url.manuscript_url) == "https://example.org/paper.pdf"
    assert by_upload.upload_token == "upload-123"
    with pytest.raises(ValidationError, match="provide exactly one"):
        CreateReviewRequest(model="gpt-5.6")
    with pytest.raises(ValidationError, match="provide exactly one"):
        CreateReviewRequest(
            manuscript_url="https://example.org/paper.pdf",
            upload_token="upload-123",
            model="gpt-5.6",
        )
