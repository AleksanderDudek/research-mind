"""Organisation management endpoints.

Endpoints
---------
GET  /org/members           list users in caller's org          (admin+)
POST /org/invite            invite a user by email               (admin+)
DELETE /org/members/{uid}   remove a user from the org           (admin+)
GET  /superadmin/orgs       list all organisations               (superadmin)
POST /superadmin/appoint    promote user to superadmin           (superadmin)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.auth.deps import AuthUserDep, invalidate_cache
from app.auth.access import require_admin, require_superadmin
from app.config import settings

router = APIRouter(tags=["org"])

_MAX_SUPERADMINS_CONFIG_KEY = "max_superadmins"
_DEFAULT_MAX_SUPERADMINS = 3


# ── Helpers ────────────────────────────────────────────────────────────────────

def _supabase_headers() -> dict[str, str]:
    return {
        "apikey":        settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def _rest(path: str) -> str:
    return f"{settings.supabase_url}/rest/v1/{path}"


def _auth(path: str) -> str:
    return f"{settings.supabase_url}/auth/v1/admin/{path}"


# ── Models ─────────────────────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str


class AppointRequest(BaseModel):
    user_id: str
    role: str = "superadmin"   # 'superadmin' | 'admin'


# ── Organisation member endpoints ──────────────────────────────────────────────

@router.get("/org/members")
def list_members(user: AuthUserDep) -> list:
    """List all profiles in the caller's organisation."""
    require_admin(user)
    import httpx
    resp = httpx.get(
        _rest("profiles"),
        headers=_supabase_headers(),
        params={"org_id": f"eq.{user.org_id}", "select": "id,role,full_name,created_at"},
    )
    resp.raise_for_status()
    return resp.json()


@router.post("/org/invite", status_code=200)
def invite_member(req: InviteRequest, user: AuthUserDep) -> dict:
    """Invite a user by email — sends a Supabase magic-link invite email."""
    require_admin(user)
    import httpx
    resp = httpx.post(
        _auth("invite"),
        headers=_supabase_headers(),
        json={
            "email": req.email,
            "data":  {"invited_org_id": user.org_id},
        },
    )
    if resp.status_code == 422:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if resp.status_code == 409:
        raise HTTPException(status_code=409, detail="User is already registered")
    if not resp.is_success:
        logger.error(f"Supabase invite failed: {resp.text}")
        raise HTTPException(status_code=502, detail="Invite email failed")
    logger.info(f"Invited {req.email!r} to org {user.org_id!r}")
    return {"invited": req.email}


@router.delete("/org/members/{member_id}", status_code=200)
def remove_member(member_id: str, user: AuthUserDep) -> dict:
    """Remove a user from the organisation (sets their org_id to null)."""
    require_admin(user)
    import httpx

    # Verify the member belongs to the same org
    check = httpx.get(
        _rest("profiles"),
        headers=_supabase_headers(),
        params={"id": f"eq.{member_id}", "org_id": f"eq.{user.org_id}", "select": "id"},
    )
    check.raise_for_status()
    if not check.json():
        raise HTTPException(status_code=404, detail="Member not found in this organisation")

    resp = httpx.patch(
        _rest("profiles"),
        headers=_supabase_headers(),
        params={"id": f"eq.{member_id}"},
        json={"org_id": None},
    )
    resp.raise_for_status()
    invalidate_cache(member_id)
    return {"removed": member_id}


# ── Superadmin endpoints ────────────────────────────────────────────────────────

@router.get("/superadmin/orgs")
def list_all_orgs(user: AuthUserDep) -> list:
    """List all organisations with member counts. Superadmins only."""
    require_superadmin(user)
    import httpx
    resp = httpx.get(
        _rest("organizations"),
        headers=_supabase_headers(),
        params={"select": "id,name,created_at,created_by"},
    )
    resp.raise_for_status()
    return resp.json()


@router.post("/superadmin/appoint", status_code=200)
def appoint_role(req: AppointRequest, user: AuthUserDep) -> dict:
    """Promote or change a user's role. Superadmins only.

    When appointing a new superadmin the current superadmin count is checked
    against the platform_config `max_superadmins` value.
    """
    require_superadmin(user)
    import httpx

    if req.role not in ("superadmin", "admin", "user"):
        raise HTTPException(status_code=400, detail="role must be superadmin, admin, or user")

    if req.role == "superadmin":
        # Enforce the superadmin seat limit
        count_resp = httpx.get(
            _rest("profiles"),
            headers=_supabase_headers(),
            params={"role": "eq.superadmin", "select": "id"},
        )
        count_resp.raise_for_status()
        current = len(count_resp.json())

        cfg_resp = httpx.get(
            _rest("platform_config"),
            headers=_supabase_headers(),
            params={"key": f"eq.{_MAX_SUPERADMINS_CONFIG_KEY}", "select": "value"},
        )
        cfg_resp.raise_for_status()
        rows = cfg_resp.json()
        limit = int(rows[0]["value"]) if rows else _DEFAULT_MAX_SUPERADMINS

        if current >= limit:
            raise HTTPException(
                status_code=403,
                detail=f"Max superadmin seats ({limit}) reached",
            )

    # Update the profile role
    resp = httpx.patch(
        _rest("profiles"),
        headers=_supabase_headers(),
        params={"id": f"eq.{req.user_id}"},
        json={"role": req.role},
    )
    resp.raise_for_status()

    # Update app_metadata so the next JWT contains the updated role
    meta_resp = httpx.put(
        _auth(f"users/{req.user_id}"),
        headers=_supabase_headers(),
        json={"app_metadata": {"role": req.role}},
    )
    if not meta_resp.is_success:
        logger.warning(f"app_metadata update failed for {req.user_id}: {meta_resp.text}")

    invalidate_cache(req.user_id)
    logger.info(f"Appointed {req.user_id!r} as {req.role!r}")
    return {"user_id": req.user_id, "role": req.role}
