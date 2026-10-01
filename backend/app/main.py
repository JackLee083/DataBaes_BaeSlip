"""FastAPI app: CORS, router registration, health. Owner: core."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_config
from app.models import HealthResponse
from app.routers import attestations, explain, keys, worker

app = FastAPI(title="BaeSlip Issuer API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list({get_config().public_web_url, "http://localhost:5173"}),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotImplementedError)
async def not_implemented(_: Request, exc: NotImplementedError) -> JSONResponse:
    # Stubs raise NotImplementedError until their owner builds them.
    return JSONResponse(status_code=501, content={"detail": f"not implemented: {exc}"})


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


app.include_router(worker.router)  # data
app.include_router(explain.router)  # rules
app.include_router(attestations.router)  # core
app.include_router(keys.router)  # core
