# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from fastapi import APIRouter

from app.api.routes import alerts, agent, auth, dashboard, products

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(alerts.router)
api_router.include_router(dashboard.router)
api_router.include_router(agent.router)

