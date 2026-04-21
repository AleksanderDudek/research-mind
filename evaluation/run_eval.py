"""
Ragas evaluation against the ResearchMind backend.

Usage:
    cd evaluation
    pip install -r requirements.txt
    BACKEND_URL=http://localhost:8001 python run_eval.py

The script:
  1. Loads Q&A pairs from datasets/qa_pairs.json
  2. Calls POST /query/ask for each question
  3. Evaluates with Ragas metrics: faithfulness, answer_relevancy, context_recall
  4. Prints a summary table and saves results to evaluation_results.json
"""

import asyncio
import json
import os
from pathlib import Path

import httpx
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_recall, faithfulness
from openai import OpenAI

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
DATASET_PATH = Path(__file__).parent / "datasets" / "qa_pairs.json"
OUTPUT_PATH = Path(__file__).parent / "evaluation_results.json"


async def query_backend(client: httpx.AsyncClient, question: str) -> dict:
    r = await client.post(
        f"{BACKEND_URL}/query/ask",
        json={"question": question},
        timeout=120,
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
                    "question": pair["question"],
                    "ground_truth": pair["ground_truth"],
                    "answer": resp.get("answer", ""),
                    "contexts": [
                        s.get("text", "") for s in resp.get("sources", []) if s.get("text")
                    ],
                })
            except Exception as e:
                print(f"  ERROR: {e}")
                results.append({
                    "question": pair["question"],
                    "ground_truth": pair["ground_truth"],
                    "answer": "",
                    "contexts": [],
                })
    return results


def run_ragas(rows: list[dict]) -> dict:
    ds = Dataset.from_list(rows)

    # Ragas uses OpenAI by default for judge LLM — point it at Ollama via LiteLLM proxy
    # or set OPENAI_API_KEY for cloud evaluation.
    llm_base = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
    llm_key = os.getenv("LITELLM_API_KEY", "sk-researchmind-local")
    llm_model = os.getenv("RAGAS_LLM_MODEL", "local-llm-small")

    from ragas.llms import LangchainLLMWrapper
    from langchain_openai import ChatOpenAI

    judge_llm = LangchainLLMWrapper(
        ChatOpenAI(
            model=llm_model,
            base_url=f"{llm_base}/v1",
            api_key=llm_key,
            temperature=0,
        )
    )

    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_community.embeddings import HuggingFaceEmbeddings

    embed_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name=embed_model)
    )

    result = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_recall],
        llm=judge_llm,
        embeddings=embeddings,
    )
    return result


def main():
    print("Loading Q&A pairs...")
    qa_pairs = json.loads(DATASET_PATH.read_text())
    print(f"  {len(qa_pairs)} pairs loaded")

    print("\nQuerying backend...")
    rows = asyncio.run(collect_responses(qa_pairs))

    answered = sum(1 for r in rows if r["answer"])
    print(f"  {answered}/{len(rows)} answered")

    if answered == 0:
        print("No answers collected — is the backend running?")
        return

    print("\nRunning Ragas evaluation...")
    result = run_ragas(rows)

    print("\n=== Results ===")
    df = result.to_pandas()
    print(df[["question", "faithfulness", "answer_relevancy", "context_recall"]].to_string(index=False))

    print("\n=== Aggregate ===")
    for metric in ["faithfulness", "answer_relevancy", "context_recall"]:
        if metric in df.columns:
            print(f"  {metric}: {df[metric].mean():.3f}")

    OUTPUT_PATH.write_text(df.to_json(orient="records", indent=2))
    print(f"\nFull results saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
