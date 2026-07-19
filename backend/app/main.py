from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.users import router as users_router

app = FastAPI(title="Digital Product Passport API")

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(users_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
