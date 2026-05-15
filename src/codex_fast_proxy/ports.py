from __future__ import annotations

import socket
from collections.abc import Iterable


def find_available_port(
    host: str,
    preferred: int,
    *,
    attempts: int = 100,
    reserved_ports: Iterable[int] = (),
) -> int | None:
    reserved = set(reserved_ports)
    for port in range(preferred, preferred + attempts):
        if port in reserved:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    return None
