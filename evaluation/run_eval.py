"""
Ragas evaluation against the ResearchMind backend.

Usage:
    cd evaluation
    .venv/bin/python run_eval.py

Env vars (all optional — defaults match backend/.env):
    BACKEND_URL        http://localhost:8001
    LITELLM_BASE_URL   http://localhost:11434   (Ollama direct)
    LITELLM_API_KEY    ollama
    RAGAS_LLM_MODEL    gemma3:12b
    EMBEDDING_MODEL    all-MiniLM-L6-v2
"""

import asyncio
import json
import os
import warnings
from pathlib import Path

import httpx
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_recall, faithfulness

warnings.filterwarnings("ignore", category=DeprecationWarning)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
DATASET_PATH = Path(__file__).parent / "datasets" / "qa_pairs.json"
OUTPUT_PATH = Path(__file__).parent / "evaluation_results.json"


async def query_backend(client: httpx.AsyncClient, question: str) -> dict:
    r = await client.post(
        f"{BACKEND_URL}/query/ask",
        json={"question": question},
        timeout=180,
    )
    r.raise_for_status()
    return r.json()


async def collect_responses(qa_pairs: list[dict]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        results = []
        for pair in qa_pairs:
            print(f"  Asking: {pair['question'][:70]}...")
            try:
                resp = await query_backend(client, pair["question"])
                results.append({
                    # Ragas 0.2.x column names
                    "user_input": pair["question"],
                    "reference": pair["ground_truth"],
                    "response": resp.get("answer", ""),
                    "retrieved_contexts": [
                        s.get("text", "")
                        for s in resp.get("sources", [])
                        if s.get("text")
                    ],
                })
            except Exception as e:
                print(f"  ERROR: {e}")
                results.append({
                    "user_input": pair["question"],
                    "reference": pair["ground_truth"],
                    "response": "",
                    "retrieved_contexts": [],
                })
    return results


def _make_judge_llm():
    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI

    llm_base = os.getenv("LITELLM_BASE_URL", "http://localhost:11434")
    llm_key = os.getenv("LITELLM_API_KEY", "ollama")
    llm_model = os.getenv("RAGAS_LLM_MODEL", "gemma3:12b")

    return LangchainLLMWrapper(
        ChatOpenAI(
            model=llm_model,
            base_url=f"{llm_base}/v1",
            api_key=llm_key,
            temperature=0,
        )
    )


def _make_embeddings():
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_huggingface import HuggingFaceEmbeddings

    embed_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    return LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name=embed_model))


def run_ragas(rows: list[dict]):
    ds = Dataset.from_list(rows)
    judge_llm = _make_judge_llm()
    embeddings = _make_embeddings()

    metrics = [faithfulness, answer_relevancy, context_recall]
    for m in metrics:
        m.llm = judge_llm
        if hasattr(m, "embeddings"):
            m.embeddings = embeddings

    return evaluate(
        ds,
        metrics=metrics,
        llm=judge_llm,
        embeddings=embeddings,
    )


def main():
    print("Loading Q&A pairs...")
    qa_pairs = json.loads(DATASET_PATH.read_text())
    print(f"  {len(qa_pairs)} pairs loaded")

    print("\nQuerying backend...")
    rows = asyncio.run(collect_responses(qa_pairs))

    answered = sum(1 for r in rows if r["response"])
    print(f"  {answered}/{len(rows)} answered")

    if answered == 0:
        print("No answers collected — is the backend running?")
        return

    print("\nRunning Ragas evaluation (this takes a few minutes with a local LLM)...")
    result = run_ragas(rows)

    df = result.to_pandas()

    print("\n=== Results ===")
    metric_cols = [c for c in ["faithfulness", "answer_relevancy", "context_recall"] if c in df.columns]
    question_col = next((c for c in ["user_input", "question"] if c in df.columns), None)
    display_cols = ([question_col] if question_col else []) + metric_cols
    if display_cols:
        print(df[display_cols].to_string(index=False))

    print("\n=== Aggregate ===")
    for metric in metric_cols:
        val = df[metric].mean()
        bar = "█" * int(val * 20)
        print(f"  {metric:<20} {val:.3f}  {bar}")

    OUTPUT_PATH.write_text(df.to_json(orient="records", indent=2))
    print(f"\nFull results saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
