from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.auth.models import UserContext
from config.settings import settings

router = APIRouter()


@router.get("/me")
async def get_me(current_user: UserContext = Depends(get_current_user)) -> dict:
    if not settings.ENABLE_DEV_ENDPOINTS:
        return {"error": "Dev endpoints disabled"}
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "groups": current_user.groups,
        "roles": current_user.roles,
        "is_admin": current_user.is_admin,
        "tenant_id": current_user.tenant_id,
    }
