import os

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

_TIMEOUT = 180.0


def _raise_for_error(r: httpx.Response) -> None:
    if r.is_error:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise ValueError(detail)


def api_get(path: str) -> dict | list:
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.get(f"{BACKEND_URL}{path}")
    _raise_for_error(r)
    return r.json()


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
    _raise_for_error(r)
    return r.json()


def api_put(path: str, json_data: dict) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.put(f"{BACKEND_URL}{path}", json=json_data)
    _raise_for_error(r)
    return r.json()


def api_delete(path: str) -> dict:
    with httpx.Client(timeout=_TIMEOUT) as client:
        r = client.delete(f"{BACKEND_URL}{path}")
    _raise_for_error(r)
    return r.json()
