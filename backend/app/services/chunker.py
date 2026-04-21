from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings


class Chunker:
    def __init__(self) -> None:
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, text: str) -> list[str]:
        return self.splitter.split_text(text)
