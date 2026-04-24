import os

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

# Short connect timeout so a missing backend fails fast;
# long read timeout for LLM inference (~3 min).
_TIMEOUT = httpx.Timeout(connect=5.0, read=180.0, write=30.0, pool=5.0)

# Audio transcription can take many minutes for large files.
_AUDIO_TIMEOUT = httpx.Timeout(connect=5.0, read=1800.0, write=120.0, pool=5.0)


def _raise_for_error(r: httpx.Response) -> None:
    if r.is_error:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise ValueError(detail)


def _request(
    method: str,
    path: str,
    *,
    json_data: dict | None = None,
    files: dict | None = None,
    timeout: httpx.Timeout = _TIMEOUT,
) -> dict | list:
    with httpx.Client(timeout=timeout) as client:
        fn = getattr(client, method)
        if files:
            r = fn(f"{BACKEND_URL}{path}", files=files)
        elif json_data is not None:
            r = fn(f"{BACKEND_URL}{path}", json=json_data)
        else:
            r = fn(f"{BACKEND_URL}{path}")
    _raise_for_error(r)
    return r.json()


def api_get(path: str) -> dict | list:
    return _request("get", path)


def api_post(
    path: str,
    json_data: dict | None = None,
    files: dict | None = None,
) -> dict:
    return _request("post", path, json_data=json_data, files=files)


def api_put(path: str, json_data: dict) -> dict:
    return _request("put", path, json_data=json_data)


def api_patch(path: str, json_data: dict) -> dict:
    return _request("patch", path, json_data=json_data)


def api_delete(path: str) -> dict:
    return _request("delete", path)


def api_post_audio(path: str, files: dict) -> dict:
    return _request("post", path, files=files, timeout=_AUDIO_TIMEOUT)
