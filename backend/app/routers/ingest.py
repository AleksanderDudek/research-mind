import asyncio
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl
from loguru import logger

from app.auth.deps import AuthUserDep
from app.auth.access import require_admin
from app.enums import DetailLevel
from app.schemas import IngestionResult
from app.services.ingest import IngestionService

router = APIRouter(prefix="/ingest", tags=["ingest"])

_400 = {400: {"description": "Bad request"}}
_500 = {500: {"description": "Internal server error"}}
_400_500 = {**_400, **_500}

_AUDIO_EXTENSIONS: frozenset[str] = frozenset({
    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4",
})
_MAX_AUDIO_MB = 100
_MAX_IMAGE_MB = 20


def _service() -> IngestionService:
    return IngestionService()


ServiceDep = Annotated[IngestionService, Depends(_service)]


class URLRequest(BaseModel):
    url: HttpUrl
    context_id: str


class TextRequest(BaseModel):
    text: str
    title: str = "Manual paste"
    context_id: str


@router.post("/pdf-url", response_model=IngestionResult, responses=_400_500)
async def ingest_pdf_from_url(req: URLRequest, user: AuthUserDep, service: ServiceDep) -> dict:
    require_admin(user)
    try:
        return await service.ingest_pdf_url(str(req.url), req.context_id, org_id=user.org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("PDF URL ingestion failed")
        raise HTTPException(status_code=500, detail="PDF URL ingestion failed")


@router.post("/web-url", response_model=IngestionResult, responses=_400_500)
async def ingest_web_page(req: URLRequest, user: AuthUserDep, service: ServiceDep) -> dict:
    require_admin(user)
    try:
        return await service.ingest_web_url(str(req.url), req.context_id, org_id=user.org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Web ingestion failed")
        raise HTTPException(status_code=500, detail="Web ingestion failed")


@router.post("/pdf-upload", response_model=IngestionResult, responses=_400_500)
async def ingest_pdf_upload(
    file: Annotated[UploadFile, File()],
    context_id: Annotated[str, Form()],
    user: AuthUserDep,
    service: ServiceDep,
) -> dict:
    require_admin(user)
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must have .pdf extension.")
    try:
        return service.ingest_pdf_bytes(
            await file.read(),
            source=file.filename or "upload.pdf",
            context_id=context_id,
            org_id=user.org_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("PDF upload ingestion failed")
        raise HTTPException(status_code=500, detail="PDF upload ingestion failed")


@router.post("/raw-text", response_model=IngestionResult, responses=_400_500)
async def ingest_raw_text(req: TextRequest, user: AuthUserDep, service: ServiceDep) -> dict:
    require_admin(user)
    if len(req.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short (min 50 characters).")
    try:
        return service.ingest_raw_text(req.text, req.title, req.context_id, org_id=user.org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Raw text ingestion failed")
        raise HTTPException(status_code=500, detail="Raw text ingestion failed")


@router.post("/image-upload", response_model=IngestionResult, responses=_400_500)
async def ingest_image(
    file: Annotated[UploadFile, File()],
    context_id: Annotated[str, Form()],
    user: AuthUserDep,
    service: ServiceDep,
    detail_level: Annotated[str, Form()] = DetailLevel.STANDARD,
) -> dict:
    require_admin(user)
    if detail_level not in DetailLevel.__members__.values():
        detail_level = DetailLevel.STANDARD
    image_bytes = await file.read()
    if len(image_bytes) > _MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Image too large (max {_MAX_IMAGE_MB} MB).")
    try:
        return await service.ingest_image_bytes(
            image_bytes=image_bytes,
            filename=file.filename or "image",
            context_id=context_id,
            detail_level=detail_level,
            org_id=user.org_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Image ingestion failed")
        raise HTTPException(status_code=500, detail="Image ingestion failed")


@router.post("/audio-upload", response_model=IngestionResult, responses=_400_500)
async def ingest_audio(
    file: Annotated[UploadFile, File()],
    context_id: Annotated[str, Form()],
    user: AuthUserDep,
    service: ServiceDep,
) -> dict:
    require_admin(user)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed: {', '.join(sorted(_AUDIO_EXTENSIONS))}",
        )
    audio_bytes = await file.read()
    if len(audio_bytes) > _MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (max {_MAX_AUDIO_MB} MB).")
    try:
        return await asyncio.to_thread(
            service.ingest_audio_bytes,
            audio_bytes=audio_bytes,
            filename=file.filename or "audio",
            context_id=context_id,
            org_id=user.org_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Audio ingestion failed")
        raise HTTPException(status_code=500, detail="Audio ingestion failed")
