from __future__ import annotations

import re
from urllib.parse import urlparse


ARXIV_ABS_PATTERN = re.compile(r"^/abs/([^/?#]+)")


def resolve_document_uri(source_uri: str) -> str:
    parsed = urlparse(source_uri)
    if parsed.netloc.lower() == "arxiv.org":
        match = ARXIV_ABS_PATTERN.match(parsed.path)
        if match:
            arxiv_id = match.group(1)
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return source_uri
