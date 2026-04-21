import trafilatura
import httpx
from loguru import logger
from app.config import settings


class WebScraper:
    async def fetch_and_extract(self, url: str) -> tuple[str, dict[str, str]]:
        async with httpx.AsyncClient(timeout=settings.request_timeout_sec) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            html = response.text

        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )
        if not text:
            raise ValueError(f"Nie udało się wyekstrahować treści z {url}")

        meta = trafilatura.extract_metadata(html)
        metadata: dict[str, str] = {
            "title": meta.title if meta and meta.title else "",
            "author": meta.author if meta and meta.author else "",
            "date": meta.date if meta and meta.date else "",
            "sitename": meta.sitename if meta and meta.sitename else "",
        }
        return text, metadata

    async def fetch_pdf(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=settings.request_timeout_sec) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            # Detect bot-protection/HTML responses served instead of PDF
            if response.content[:5] not in (b"%PDF-", b"%pdf-"):
                if b"<html" in response.content[:512].lower():
                    raise ValueError(
                        "Serwer zwrócił stronę HTML zamiast PDF (bot-protection?). "
                        "Spróbuj pobrać plik ręcznie i użyj opcji 'Upload PDF'."
                    )
                if "pdf" not in content_type.lower():
                    logger.warning(f"URL może nie być PDF-em: {content_type}")

            size_mb = len(response.content) / (1024 * 1024)
            if size_mb > settings.max_pdf_size_mb:
                raise ValueError(
                    f"PDF za duży: {size_mb:.1f}MB > {settings.max_pdf_size_mb}MB"
                )

            return response.content
