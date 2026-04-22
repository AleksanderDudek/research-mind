"""
PySpark batch ingestion job.

Usage:
    spark-submit spark/jobs/batch_ingest.py --input data/urls.csv

CSV format (one row per document):
    url,title
    https://arxiv.org/pdf/2005.11401.pdf,RAG paper
    https://example.com/paper.pdf,Some paper

Environment variables (same as backend):
    QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY, QDRANT_LOCAL_PATH
    QDRANT_COLLECTION (default: research_papers)
    EMBEDDING_MODEL   (default: all-MiniLM-L6-v2)
    EMBEDDING_DIM     (default: 384)
"""

import argparse
import io
import os
import uuid
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import ArrayType, StringType, StructField, StructType

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "research_papers")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


# ── Chunk text ────────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + CHUNK_SIZE
        chunks.append(" ".join(words[start:end]))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c.split()) >= 20]


# ── Extract text from URL ─────────────────────────────────────────────────────

def fetch_text(url: str) -> str:
    resp = requests.get(url, timeout=30, headers={"User-Agent": "ResearchMind/1.0"})
    resp.raise_for_status()

    if url.lower().endswith(".pdf") or "application/pdf" in resp.headers.get("Content-Type", ""):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(resp.content))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    else:
        from html.parser import HTMLParser

        class _Strip(HTMLParser):
            def __init__(self):
                super().__init__()
                self._parts = []

            def handle_data(self, data):
                self._parts.append(data)

        p = _Strip()
        p.feed(resp.text)
        return " ".join(p._parts)


# ── Spark UDF: (url, title) → list of chunk strings ──────────────────────────

def extract_chunks(url: str, title: str) -> list[str]:
    try:
        text = fetch_text(url)
        return chunk_text(text)
    except Exception as e:
        print(f"[WARN] Failed to process {url}: {e}")
        return []


# ── Qdrant upsert (runs on driver after collect) ──────────────────────────────

def upsert_to_qdrant(rows: list[dict]) -> None:
    from qdrant_client import QdrantClient, models
    from qdrant_client.models import Distance, PointStruct, VectorParams
    from sentence_transformers import SentenceTransformer

    if QDRANT_LOCAL_PATH:
        client = QdrantClient(path=QDRANT_LOCAL_PATH)
    elif QDRANT_API_KEY:
        client = QdrantClient(url=f"https://{QDRANT_HOST}", api_key=QDRANT_API_KEY)
    else:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Ensure collection exists
    collections = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in collections:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION,
            field_name="source_type",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=QDRANT_COLLECTION,
            field_name="document_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    model = SentenceTransformer(EMBEDDING_MODEL)

    batch_size = 64
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        texts = [r["chunk"] for r in batch]
        vectors = model.encode(texts, show_progress_bar=False).tolist()

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "document_id": r["document_id"],
                    "title": r["title"],
                    "source": r["url"],
                    "source_type": "pdf" if r["url"].lower().endswith(".pdf") else "web",
                    "text": r["chunk"],
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "chunk_index": r["chunk_index"],
                },
            )
            for r, vec in zip(batch, vectors)
        ]
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        print(f"  Upserted {len(points)} points (batch {i // batch_size + 1})")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to CSV file with url,title columns")
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("ResearchMind-BatchIngest")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.option("header", "true").csv(args.input)

    if "url" not in df.columns:
        raise ValueError("CSV must have a 'url' column")
    if "title" not in df.columns:
        df = df.withColumn("title", col("url"))

    urls = df.select("url", "title").collect()
    print(f"Processing {len(urls)} URLs...")

    all_rows = []
    for row in urls:
        url = row["url"].strip()
        title = row["title"].strip() if row["title"] else url
        document_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))

        chunks = extract_chunks(url, title)
        print(f"  {url} → {len(chunks)} chunks")

        for idx, chunk in enumerate(chunks):
            all_rows.append(
                {
                    "document_id": document_id,
                    "url": url,
                    "title": title,
                    "chunk": chunk,
                    "chunk_index": idx,
                }
            )

    if not all_rows:
        print("No chunks to ingest. Exiting.")
        return

    print(f"\nUpserting {len(all_rows)} total chunks to Qdrant...")
    upsert_to_qdrant(all_rows)
    print("Done.")

    spark.stop()


if __name__ == "__main__":
    main()
