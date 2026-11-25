"""Erros de domínio e formato único de resposta de erro: {"error": {code, message, details}}."""
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso não encontrado", details: Any = None):
        super().__init__(404, "not_found", message, details)


class ConflictError(AppError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(409, "conflict", message, details)


class ValidationFailure(AppError):
    def __init__(self, message: str, details: Any = None):
        super().__init__(422, "validation_error", message, details)


def _body(code: str, message: str, details: Any = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e.get("loc", []) if p != "body"), "message": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content=_body("validation_error", "Dados inválidos", details))
