"""Role-guard helpers for FastAPI route handlers."""
from fastapi import HTTPException, status
from .deps import AuthUser


def require_admin(user: AuthUser) -> None:
    """Raise 403 if caller is not at least an admin."""
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")


def require_superadmin(user: AuthUser) -> None:
    """Raise 403 if caller is not a superadmin."""
    if user.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmins only")


def assert_same_org(user: AuthUser, org_id: str) -> None:
    """Raise 403 unless caller is superadmin or belongs to org_id."""
    if user.role == "superadmin":
        return
    if user.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong organisation")
