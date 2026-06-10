from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api import exports, processing, projects


PROJECTS_ROOT = Path("projects")


def create_app(projects_root: Path | None = None) -> FastAPI:
    app = FastAPI()
    app.state.projects_root = projects_root or PROJECTS_ROOT
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type", "x-filename", "x-sample-every-n-frames"],
    )
    app.include_router(projects.router)
    app.include_router(processing.router)
    app.include_router(exports.router)
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
