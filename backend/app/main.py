from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.routers import ingest, query


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("ResearchMind API starting up...")
    yield
    logger.info("ResearchMind API shutting down.")


app = FastAPI(
    title="ResearchMind API",
    version="0.1.0",
    description="Platforma RAG do analizy badań naukowych",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(query.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
