from fastapi import APIRouter, Depends

from app.core.auth import check_role, check_permission, get_current_user
from app.models.models import User

router = APIRouter()


@router.get("/admin")
def admin_only(current_user: User = Depends(check_role("admin"))):
    """Admin-only endpoint. Requires 'admin' role."""
    return {
        "message": f"Welcome, admin {current_user.username}!",
        "role": current_user.role.name,
        "permissions": current_user.role.permissions,
        "email": current_user.email
    }


@router.get("/protected")
def protected_route(current_user: User = Depends(check_role("user"))):
    """User-protected endpoint. Requires 'user' or higher role."""
    return {
        "message": f"Hello, {current_user.username}!",
        "role": current_user.role.name,
        "permissions": current_user.role.permissions
    }


@router.get("/read-only")
def read_only_endpoint(current_user: User = Depends(check_permission("read"))):
    """Endpoint requiring 'read' permission. Any role with read permission can access."""
    return {
        "message": f"Hello {current_user.username}, you have read permission",
        "role": current_user.role.name,
        "permissions": current_user.role.permissions
    }


@router.post("/write-resource")
def write_resource(current_user: User = Depends(check_permission("write"))):
    """Endpoint requiring 'write' permission."""
    return {
        "message": f"Resource created by {current_user.username}",
        "role": current_user.role.name,
        "action": "write"
    }


@router.delete("/admin-delete")
def admin_delete(current_user: User = Depends(check_permission("delete"))):
    """Endpoint requiring 'delete' permission (admin only)."""
    return {
        "message": f"Resource deleted by {current_user.username}",
        "role": current_user.role.name,
        "action": "delete"
    }


@router.get("/users-info")
def list_users_info(current_user: User = Depends(check_role("admin"))):
    """Admin endpoint to view user information. Admin role only."""
    return {
        "current_user": {
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role.name
        },
        "message": "Only admins can see this information"
    }

