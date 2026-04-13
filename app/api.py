from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.auth import authenticate_token
from app.database import SessionLocal
from app.models import (  # noqa: F401
    ComponentTemplateDB,
    ComponentTemplateItemDB,
    DeviceTokenDB,
    ItemComponentDB,
    ItemDB,
    ItemHistoryDB,
    ItemPhotoDB,
    LocationDB,
    NotificationDB,
    RoleDB,
    RentalDB,
    RepairDB,
    TransferDB,
    UserDB,
    WriteOffDB,
)
from app.realtime import realtime_manager
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


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("access_token") or websocket.headers.get("authorization")
    if not token:
        await websocket.close(code=4401, reason="Missing access token")
        return
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    db = SessionLocal()
    try:
        user = authenticate_token(token, db)
        await realtime_manager.connect(user.id, websocket)
        await websocket.send_json(
            {
                "type": "connected",
                "user_id": user.id,
                "message": "Realtime connection established",
            }
        )
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        await websocket.close(code=4401, reason="Unauthorized")
    finally:
        try:
            if "user" in locals():
                await realtime_manager.disconnect(user.id, websocket)
        finally:
            db.close()
