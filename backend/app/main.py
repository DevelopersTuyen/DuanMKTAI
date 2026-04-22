from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.services.automation import automation_manager
from app.services.local_image_generation import probe_local_image_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "Backend starting: app=%s api_prefix=%s backend=%s",
        settings.app_name,
        settings.api_prefix,
        settings.public_backend_url,
    )
    logger.info(
        "Ollama config: base_url=%s model=%s",
        settings.ollama_base_url,
        settings.ollama_model,
    )
    logger.info(
        "Local image config: provider=%s a1111=%s comfyui=%s workflow=%s",
        settings.local_image_provider,
        settings.automatic1111_base_url,
        settings.comfyui_base_url,
        settings.comfyui_workflow_file or "(none)",
    )
    image_ok, image_message = await probe_local_image_provider(settings)
    if image_ok:
        logger.info("Local image status: %s", image_message)
    else:
        logger.warning("Local image status: %s", image_message)
    await automation_manager.start()
    logger.info("Automation manager started.")
    try:
        yield
    finally:
        await automation_manager.stop()
        logger.info("Automation manager stopped.")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": settings.app_name}
