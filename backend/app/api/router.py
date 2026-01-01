from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.agent import router as agent_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.ping import router as ping_router
from app.api.routes.tickets import router as tickets_router

api_router = APIRouter()
api_router.include_router(ping_router)
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(tickets_router)
api_router.include_router(agent_router)
