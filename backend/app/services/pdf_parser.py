from pypdf import PdfReader
from io import BytesIO
from loguru import logger


class PDFParser:
    def parse_bytes(self, pdf_bytes: bytes) -> str:
        reader = PdfReader(BytesIO(pdf_bytes))
        texts: list[str] = []
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    texts.append(text)
            except Exception as e:
                logger.warning(f"Failed to extract page {i}: {e}")
        return "\n\n".join(texts)

    def metadata(self, pdf_bytes: bytes) -> dict[str, str | int]:
        reader = PdfReader(BytesIO(pdf_bytes))
        meta = reader.metadata or {}
        return {
            "title": str(meta.get("/Title", "") or ""),
            "author": str(meta.get("/Author", "") or ""),
            "num_pages": len(reader.pages),
        }
