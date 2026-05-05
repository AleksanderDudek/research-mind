"""FastAPI dependency: verify Supabase JWT and resolve caller's org + role.

Strategy
--------
1. Verify the JWT using Supabase's JWKS endpoint (supports both ES256 and HS256).
   ES256 is the default for newer Supabase projects; HS256 for legacy ones.
   The JWKS client caches the public key locally for 10 minutes.
2. Extract user_id from `sub` claim.
3. Fetch org_id + role from the `profiles` table via Supabase REST API,
   with a short in-process TTL cache so we don't hit Supabase on every request.
4. Return an AuthUser dataclass that routers can use for access control.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Annotated

import httpx
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.config import settings

# ── In-process caches ─────────────────────────────────────────────────────────
_CACHE_TTL = 60  # profile cache TTL in seconds
_profile_cache: dict[str, tuple[float, "AuthUser"]] = {}
_jwks_client: PyJWKClient | None = None   # singleton, lazy-init


@dataclass
class AuthUser:
    user_id:  str
    org_id:   str
    role:     str   # 'superadmin' | 'admin' | 'user'
    email:    str = ""


# ── JWT verification ──────────────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=True)


def _get_jwks_client() -> PyJWKClient:
    """Return (and lazily create) the singleton JWKS client.

    Fetches Supabase's public keys from:
      {SUPABASE_URL}/auth/v1/.well-known/jwks.json
    Works for both ES256 (new projects) and HS256 (legacy projects).
    Keys are cached locally for 10 minutes.
    """
    global _jwks_client
    if _jwks_client is None:
        url = settings.supabase_url
        if not url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth not configured (SUPABASE_URL missing)",
            )
        _jwks_client = PyJWKClient(
            f"{url}/auth/v1/.well-known/jwks.json",
            cache_jwk_set=True,
            lifespan=600,   # 10-minute local key cache
        )
    return _jwks_client


def _decode_jwt(token: str) -> dict:
    """Verify Supabase JWT using JWKS public key. Raises 401/503 on failure."""
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "HS256"],   # ES256 = new Supabase, HS256 = legacy
            audience="authenticated",
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError as exc:
        logger.debug(f"JWT decode failed: {exc}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"JWKS fetch failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        )


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

    # Slow path: fetch from Supabase profiles table (cached 60 s)
    auth_user = _fetch_profile(user_id)
    auth_user.email = payload.get("email", "")
    return auth_user


AuthUserDep = Annotated[AuthUser, Depends(get_current_user)]
