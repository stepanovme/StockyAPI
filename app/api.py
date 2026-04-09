from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.models import (  # noqa: F401
    ComponentTemplateDB,
    ComponentTemplateItemDB,
    ItemComponentDB,
    ItemDB,
    ItemHistoryDB,
    ItemPhotoDB,
    LocationDB,
    RoleDB,
    TransferDB,
    UserDB,
    WriteOffDB,
)
from app.routes import main_router

app = FastAPI(
    title="Stocky API",
    version="1.0.0",
    debug=True,
)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", "HTTP error")
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)
    return _error_response(exc.status_code, code, message)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in first_error.get("loc", []))
    message = first_error.get("msg", "Validation error")
    if location:
        message = f"{location}: {message}"
    return _error_response(422, "VALIDATION_ERROR", message)


app.include_router(main_router)
