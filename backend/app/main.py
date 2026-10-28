import uuid
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.api import auth, insights, planning, projects, raid, work_items
from app.config import get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-requested-with"

Handler = Callable[[Request], Awaitable[Response]]


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ProjectForge AI API",
        version="0.1.0",
        description="Domain API for ProjectForge AI. All tenant data is scoped to the caller's "
        "active organization (header `X-Org-Id`, defaulting to the first membership).",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next: Handler) -> Response:
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        # CSRF defence in depth on top of SameSite=Lax: browsers cannot send a custom header
        # cross-origin without a CORS preflight, which this API never grants.
        if (
            request.method not in SAFE_METHODS
            and request.url.path.startswith("/api/")
            and settings.session_cookie_name in request.cookies
            and request.headers.get(CSRF_HEADER) is None
        ):
            return JSONResponse({"detail": "Missing X-Requested-With header"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.path.startswith("/api/") and request.url.path != "/api/docs":
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    api = APIRouter(prefix="/api")

    @api.get("/healthz", tags=["meta"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    for module in (auth, projects, work_items, planning, raid, insights):
        api.include_router(module.router)
    app.include_router(api)
    return app


app = create_app()
