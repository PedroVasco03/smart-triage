"""Smart Triage - API do agente baseado em utilidade.

Executar:  uvicorn main:app --reload --port 8000
Documentação interativa (Swagger/OpenAPI): http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.database.init_db import init_db

DISCLAIMER = (
    "Projeto académico e experimental. Usa dados sintéticos. As pontuações são parâmetros de simulação "
    "e NÃO constituem triagem clínica, diagnóstico nem substituem profissionais de saúde."
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    init_db(create_tables=settings.auto_create_tables)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0", description=DISCLAIMER, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["Sistema"])
    def health():
        return {"status": "ok", "disclaimer": DISCLAIMER}

    return app


app = create_app()
