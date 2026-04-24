import asyncio
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl
from loguru import logger

from app.services.ingestion import IngestionService

router = APIRouter(prefix="/ingest", tags=["ingest"])

_400 = {400: {"description": "Bad request"}}
_500 = {500: {"description": "Internal server error"}}
_400_500 = {**_400, **_500}


def get_service() -> IngestionService:
    return IngestionService()


ServiceDep = Annotated[IngestionService, Depends(get_service)]


class URLRequest(BaseModel):
    url: HttpUrl
    context_id: str


class TextRequest(BaseModel):
    text: str
    title: str = "Manual paste"
    context_id: str


@router.post("/pdf-url", responses=_400_500)
async def ingest_pdf_from_url(req: URLRequest, service: ServiceDep) -> dict:
    """Źródło 1: link do pliku PDF."""
    try:
        return await service.ingest_pdf_url(str(req.url), req.context_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("PDF URL ingestion failed")
        raise HTTPException(status_code=500, detail="PDF URL ingestion failed")


@router.post("/web-url", responses=_400_500)
async def ingest_web_page(req: URLRequest, service: ServiceDep) -> dict:
    """Źródło 2: link do strony WWW."""
    try:
        return await service.ingest_web_url(str(req.url), req.context_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Web ingestion failed")
        raise HTTPException(status_code=500, detail="Web ingestion failed")


@router.post("/pdf-upload", responses=_400_500)
async def ingest_pdf_upload(
    file: Annotated[UploadFile, File(...)],
    context_id: Annotated[str, Form()],
    service: ServiceDep,
) -> dict:
    """Źródło 3: upload pliku PDF."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Plik musi mieć rozszerzenie .pdf")
    try:
        pdf_bytes = await file.read()
        return service.ingest_pdf_bytes(pdf_bytes, source=file.filename, context_id=context_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("PDF upload ingestion failed")
        raise HTTPException(status_code=500, detail="PDF upload ingestion failed")


@router.post("/raw-text", responses=_400_500)
async def ingest_raw_text(req: TextRequest, service: ServiceDep) -> dict:
    """Źródło 4: wklejony tekst."""
    if len(req.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Tekst za krótki (min. 50 znaków).")
    try:
        return service.ingest_raw_text(req.text, req.title, req.context_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Raw text ingestion failed")
        raise HTTPException(status_code=500, detail="Raw text ingestion failed")


_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}
_MAX_AUDIO_MB = 100
_MAX_IMAGE_MB = 20


@router.post("/image-upload", responses=_400_500)
async def ingest_image(
    file: Annotated[UploadFile, File(...)],
    context_id: Annotated[str, Form()],
    service: ServiceDep,
    detail_level: Annotated[str, Form()] = "standard",
) -> dict:
    """Źródło 5: wgrany obraz — opisany przez model wizyjny i zindeksowany."""
    if detail_level not in ("quick", "standard", "detailed"):
        detail_level = "standard"
    image_bytes = await file.read()
    if len(image_bytes) > _MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Image too large (max {_MAX_IMAGE_MB} MB).")
    try:
        return await service.ingest_image_bytes(
            image_bytes=image_bytes,
            filename=file.filename or "image",
            context_id=context_id,
            detail_level=detail_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Image ingestion failed")
        raise HTTPException(status_code=500, detail="Image ingestion failed")


@router.post("/audio-upload", responses=_400_500)
async def ingest_audio(
    file: Annotated[UploadFile, File(...)],
    context_id: Annotated[str, Form()],
    service: ServiceDep,
) -> dict:
    """Źródło 6: wgrany plik audio — transkrybowany przez Whisper i zindeksowany."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format. Allowed: {', '.join(_AUDIO_EXTENSIONS)}")
    audio_bytes = await file.read()
    if len(audio_bytes) > _MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large (max {_MAX_AUDIO_MB} MB).")
    try:
        return await asyncio.to_thread(
            service.ingest_audio_bytes,
            audio_bytes=audio_bytes,
            filename=file.filename or "audio",
            context_id=context_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Audio ingestion failed")
        raise HTTPException(status_code=500, detail="Audio ingestion failed")
