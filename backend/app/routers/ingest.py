from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, HttpUrl
from loguru import logger

from app.services.ingestion import IngestionService

router = APIRouter(prefix="/ingest", tags=["ingest"])
service = IngestionService()


class URLRequest(BaseModel):
    url: HttpUrl


class TextRequest(BaseModel):
    text: str
    title: str = "Manual paste"


@router.post("/pdf-url")
async def ingest_pdf_from_url(req: URLRequest) -> dict:
    """Źródło 1: link do pliku PDF."""
    try:
        return await service.ingest_pdf_url(str(req.url))
    except Exception as e:
        logger.exception("PDF URL ingestion failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/web-url")
async def ingest_web_page(req: URLRequest) -> dict:
    """Źródło 2: link do strony WWW."""
    try:
        return await service.ingest_web_url(str(req.url))
    except Exception as e:
        logger.exception("Web ingestion failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pdf-upload")
async def ingest_pdf_upload(file: UploadFile = File(...)) -> dict:
    """Źródło 3: upload pliku PDF."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Plik musi mieć rozszerzenie .pdf")
    try:
        pdf_bytes = await file.read()
        return await service.ingest_pdf_bytes(pdf_bytes, source=file.filename)
    except Exception as e:
        logger.exception("PDF upload ingestion failed")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/raw-text")
async def ingest_raw_text(req: TextRequest) -> dict:
    """Źródło 4: wklejony tekst."""
    if len(req.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Tekst za krótki (min. 50 znaków).")
    try:
        return await service.ingest_raw_text(req.text, req.title)
    except Exception as e:
        logger.exception("Raw text ingestion failed")
        raise HTTPException(status_code=400, detail=str(e))
