from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.models import SessionState


DEFAULT_UPLOAD_DIR = Path("uploads")


def create_app(upload_dir: Path | None = None) -> FastAPI:
    app = FastAPI()
    app.state.session = SessionState()
    app.state.upload_dir = str((upload_dir or DEFAULT_UPLOAD_DIR).resolve())
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type", "x-filename", "x-sample-every-n-frames"],
    )
    app.include_router(router)
    _install_error_handlers(app)
    return app


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(LookupError)
    async def lookup_error_handler(request: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": str(exc)})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    @app.exception_handler(FileExistsError)
    async def file_exists_error_handler(request: Request, exc: FileExistsError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(exc)})


app = create_app()
