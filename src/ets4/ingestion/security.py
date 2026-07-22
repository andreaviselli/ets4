"""URL validation for narrowly scoped manuscript fetching."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit


class UnsafeUrlError(ValueError):
    """Raised when a URL could reach a non-public network resource."""


Resolver = Callable[..., Any]


def _is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_url(url: str, resolver: Resolver = socket.getaddrinfo) -> str:
    """Validate syntax, credentials, ports, and all currently resolved addresses."""

    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("manuscript URL must use http or https")
    if not parsed.hostname:
        raise UnsafeUrlError("manuscript URL must include a hostname")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("credentials are not allowed in manuscript URLs")
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeUrlError("manuscript URL contains an invalid port") from exc
    if port not in {None, 80, 443}:
        raise UnsafeUrlError("manuscript URL must use port 80 or 443")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise UnsafeUrlError("local hostnames are not allowed")
    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        literal_address = None
    if literal_address is not None and not _is_public_address(str(literal_address)):
        raise UnsafeUrlError("manuscript hostname resolves to a non-public address")

    try:
        records = resolver(
            hostname, port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise UnsafeUrlError(f"cannot resolve manuscript hostname: {hostname}") from exc
    addresses = {str(record[4][0]) for record in records}
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise UnsafeUrlError("manuscript hostname resolves to a non-public address")

    netloc = hostname
    if port is not None:
        netloc = f"{hostname}:{port}"
    normalized = SplitResult(
        scheme=parsed.scheme,
        netloc=netloc,
        path=parsed.path or "/",
        query=parsed.query,
        fragment="",
    )
    return urlunsplit(normalized)
