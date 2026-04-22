import os

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

_TIMEOUT = 180.0


def api_post(
    path: str,
    json_data: dict | None = None,
    files: dict | None = None,
) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as client:
        if files:
            r = client.post(f"{BACKEND_URL}{path}", files=files)
        else:
            r = client.post(f"{BACKEND_URL}{path}", json=json_data)

    if r.is_error:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise ValueError(detail)

    return r.json()
