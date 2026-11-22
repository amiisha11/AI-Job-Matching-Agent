"""FastAPI application for the local job-matching demo.

This process is the only one that should open the database. Authentication
tables are prepared when the server starts, not when this module is imported.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from settings import get_cors_origins
from routes.auth import router as auth_router
from routes.candidates import router as candidates_router
from routes.jobs import router as jobs_router
from routes.preparation import router as preparation_router
from routes.resume import router as resume_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Prepare auth and preparation tables. Job-source columns stay a separate command."""
    from database import ensure_auth_schema, ensure_preparation_schema

    ensure_auth_schema()
    ensure_preparation_schema()
    yield


app = FastAPI(
    title="AI Job Matching Agent",
    description="Local API for candidate profiles, job listings, and saved jobs.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(candidates_router)
app.include_router(jobs_router)
app.include_router(preparation_router)
app.include_router(resume_router)


@app.exception_handler(RequestValidationError)
async def hide_rejected_values(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Describe invalid fields without echoing passwords or other submitted values."""
    parts: list[str] = []
    for item in exc.errors():
        location = [str(part) for part in item.get("loc", []) if part not in ("body", "query", "header")]
        field = location[-1] if location else "field"
        if any(word in field for word in ("password", "token", "claim", "otp")):
            parts.append("Check the password and try again.")
            continue
        parts.append(f"{field}: {item.get('msg', 'Invalid value')}")
    detail = " ".join(parts) or "Check the form and try again."
    return JSONResponse(status_code=422, content={"detail": detail})


@app.get("/")
def root() -> dict[str, str]:
    """Report that the API process is up."""
    return {
        "status": "ok",
        "message": "AI Job Matching Agent API is running.",
    }
