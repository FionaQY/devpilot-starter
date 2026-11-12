import logging

from fastapi import FastAPI

from devpilot.api.routes import router
from devpilot.providers import get_provider_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="DevPilot",
    description="A read-only AI software engineering agent with multi-provider failover.",
    version="0.2.0",
)

app.include_router(router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/providers", tags=["health"])
def provider_status() -> dict[str, list[str]]:
    """Which providers are configured, in failover order (names only, never keys)."""
    return {"providers": get_provider_pool().names}