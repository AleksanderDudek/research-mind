"""FastAPI dependency: verify Supabase JWT and resolve caller's org + role.

Strategy
--------
1. Decode the Supabase JWT locally (no network call) using SUPABASE_JWT_SECRET.
2. Extract user_id from `sub` claim.
3. Fetch org_id + role from the `profiles` table via Supabase REST API,
   with a short in-process TTL cache so we don't hit Supabase on every request.
4. Return an AuthUser dataclass that routers can use for access control.

The TTL cache means role changes propagate within ~60 s — acceptable for SaaS.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Annotated

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.config import settings

# ── In-process profile cache ──────────────────────────────────────────────────
_CACHE_TTL = 60  # seconds
_profile_cache: dict[str, tuple[float, "AuthUser"]] = {}


@dataclass
class AuthUser:
    user_id:  str
    org_id:   str
    role:     str   # 'superadmin' | 'admin' | 'user'
    email:    str = ""


# ── JWT verification ──────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=True)


def _decode_jwt(token: str) -> dict:
    """Verify Supabase JWT signature and return payload. Raises 401 on failure."""
    secret = settings.supabase_jwt_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured (SUPABASE_JWT_SECRET missing)",
        )
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError as exc:
        logger.debug(f"JWT decode failed: {exc}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ── Profile fetch (cached) ────────────────────────────────────────────────────

def _fetch_profile(user_id: str) -> AuthUser:
    """Query Supabase profiles table for org_id and role.

    Uses service-role key so Row-Level Security is bypassed.
    Result is cached in-process for _CACHE_TTL seconds.
    """
    now = time.monotonic()
    cached = _profile_cache.get(user_id)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1]

    url = f"{settings.supabase_url}/rest/v1/profiles"
    headers = {
        "apikey":        settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Accept":        "application/json",
    }
    params = {"id": f"eq.{user_id}", "select": "id,org_id,role"}

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=5.0)
        resp.raise_for_status()
        rows = resp.json()
    except Exception as exc:
        logger.error(f"Supabase profile fetch failed for {user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        )

    if not rows:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile not found")

    row = rows[0]
    auth_user = AuthUser(
        user_id=user_id,
        org_id=row.get("org_id") or "",
        role=row.get("role") or "user",
    )
    _profile_cache[user_id] = (now, auth_user)
    return auth_user


def invalidate_cache(user_id: str) -> None:
    """Remove cached profile entry — call after role/org changes."""
    _profile_cache.pop(user_id, None)


# ── FastAPI dependency ─────────────────────────────────────────────────────────

def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> AuthUser:
    """Verify Supabase JWT and return caller's AuthUser. Inject via Depends()."""
    payload = _decode_jwt(creds.credentials)
    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token sub")

    # Fast path: if app_metadata already has org_id + role skip the DB call
    meta = payload.get("app_metadata", {})
    if meta.get("org_id") and meta.get("role"):
        return AuthUser(
            user_id=user_id,
            org_id=meta["org_id"],
            role=meta["role"],
            email=payload.get("email", ""),
        )

    # Slow path: fetch from Supabase (cached 60 s)
    auth_user = _fetch_profile(user_id)
    auth_user.email = payload.get("email", "")
    return auth_user


AuthUserDep = Annotated[AuthUser, Depends(get_current_user)]
