from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.ai_extraction import router as ai_extraction_router
from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.lifecycle_events import router as lifecycle_events_router
from app.routers.organizations import router as organizations_router
from app.routers.passports import router as passports_router
from app.routers.support_tickets import router as support_tickets_router
from app.routers.product_items import router as product_items_router
from app.routers.product_models import router as product_models_router
from app.routers.templates import router as templates_router
from app.routers.team_members import router as team_members_router
from app.routers.users import router as users_router

app = FastAPI(title="Digital Product Passport API")

# Browsers may call the API only from the configured frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

app.include_router(auth_router)
app.include_router(ai_extraction_router)
app.include_router(categories_router)
app.include_router(lifecycle_events_router)
app.include_router(organizations_router)
app.include_router(passports_router)
app.include_router(support_tickets_router)
app.include_router(product_items_router)
app.include_router(product_models_router)
app.include_router(templates_router)
app.include_router(team_members_router)
app.include_router(users_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
