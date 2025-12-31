from fastapi import APIRouter, Depends

from app.core.auth import check_role
from app.models.models import User

router = APIRouter()

@router.get("/admin")
def admin_only(current_user: User = Depends(check_role("admin"))):
    """Admin-only endpoint example."""
    return {
        "message": f"Welcome, admin {current_user.username}!",
        "role": current_user.role.name,
        "permissions": current_user.role.permissions
    }

@router.get("/protected")
def protected_route(current_user: User = Depends(check_role("user"))):
    """User-protected endpoint example."""
    return {
        "message": f"Hello, {current_user.username}!",
        "role": current_user.role.name,
        "permissions": current_user.role.permissions
    }
