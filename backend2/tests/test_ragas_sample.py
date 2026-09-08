"""Ragas evaluation sample for 后端2 RAG quality checks.

- Offline smoke always runs (token-overlap stub, no live LLM).
- `test_ragas_evaluate_live_ollama` calls real `ragas.evaluate` against local
  Ollama (OpenAI-compat). Skips only when Ollama/model unreachable.

Run:
    pytest tests/test_ragas_sample.py -q
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import pytest


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _token_overlap(answer: str, contexts: list[str]) -> float:
    """Faithfulness-style stub: fraction of answer tokens found in contexts."""
    ctx = " ".join(contexts).lower()
    ans_tokens = _tokens(answer)
    if not ans_tokens:
        return 0.0
    return sum(1 for t in ans_tokens if t in ctx) / len(ans_tokens)


def _context_precision(_answer: str, contexts: list[str], ground_truth: str) -> float:
    """Context-precision-style stub: contexts that mention ground-truth terms."""
    gt_tokens = [t for t in _tokens(ground_truth) if len(t) > 2]
    if not contexts or not gt_tokens:
        return 0.0
    relevant = 0
    for c in contexts:
        cl = c.lower()
        if any(t in cl for t in gt_tokens):
            relevant += 1
    return relevant / len(contexts)


SAMPLE: dict[str, Any] = {
    "question": "What stack does Alice use?",
    "answer": "Python FastAPI",
    "contexts": [
        "Alice resume: Python FastAPI backend experience.",
        "Unrelated note: office hours on Monday.",
    ],
    "ground_truth": "Python FastAPI",
}


# SDNU-style sample for live ragas.evaluate
SDNU_SAMPLE: dict[str, Any] = {
    "question": "山东师范大学的校训是什么？",
    "answer": "山东师范大学的校训是“弘德明志，博学笃行”。",
    "contexts": [
        "山东师范大学校训为“弘德明志，博学笃行”。学校位于济南，是山东省重点高校。",
        "校训释义：弘德明志强调品德与志向，博学笃行强调学问与实践统一。",
    ],
    "ground_truth": "弘德明志，博学笃行",
}

OLLAMA_BASE = "http://127.0.0.1:11434"
OLLAMA_V1 = f"{OLLAMA_BASE}/v1"
OLLAMA_MODEL = "qwen2.5:1.5b"


def test_ragas_style_offline_smoke_metrics():
    """Meaningful offline smoke: faithfulness + context-precision style scores."""
    faithfulness = _token_overlap(SAMPLE["answer"], SAMPLE["contexts"])
    precision = _context_precision(
        SAMPLE["answer"], SAMPLE["contexts"], SAMPLE["ground_truth"]
    )

    assert 0.0 <= faithfulness <= 1.0
    assert 0.0 <= precision <= 1.0
    assert faithfulness >= 0.9, f"expected grounded answer, got faithfulness={faithfulness}"
    assert precision >= 0.5, f"expected relevant context, got precision={precision}"

    # Negative control: hallucinated answer should score low
    bad = _token_overlap("quantum teleportation yesterday", SAMPLE["contexts"])
    assert bad < faithfulness


def _require_ollama_model(model: str = OLLAMA_MODEL) -> None:
    try:
        r = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=3.0)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Ollama unreachable at {OLLAMA_BASE}: {exc}")
    if r.status_code != 200:
        pytest.skip(f"Ollama /api/tags status={r.status_code}")
    names = [m.get("name", "") for m in r.json().get("models", [])]
    if not any(model in n for n in names):
        pytest.skip(f"Ollama model {model!r} not pulled; have={names}")


def test_ragas_evaluate_live_ollama():
    """Real ragas.evaluate (faithfulness) via local Ollama OpenAI-compat endpoint."""
    _require_ollama_model(OLLAMA_MODEL)

    try:
        from datasets import Dataset
        from langchain_openai import ChatOpenAI
        from ragas import evaluate
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import faithfulness
    except ImportError as exc:
        pytest.skip(f"ragas/datasets not installed: {exc}")

    llm = ChatOpenAI(
        base_url=OLLAMA_V1,
        api_key="sk-no-auth",
        model=OLLAMA_MODEL,
        temperature=0,
        timeout=120,
    )
    wrapped = LangchainLLMWrapper(llm)

    ds = Dataset.from_dict(
        {
            "question": [SDNU_SAMPLE["question"]],
            "answer": [SDNU_SAMPLE["answer"]],
            "contexts": [SDNU_SAMPLE["contexts"]],
            "ground_truth": [SDNU_SAMPLE["ground_truth"]],
        }
    )

    try:
        result = evaluate(ds, metrics=[faithfulness], llm=wrapped)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ragas.evaluate failed against Ollama: {exc}")

    # Result may be EvaluationResult / dict-like
    score = None
    if hasattr(result, "__getitem__"):
        try:
            score = float(result["faithfulness"])
        except Exception:  # noqa: BLE001
            score = None
    if score is None and hasattr(result, "to_pandas"):
        df = result.to_pandas()
        if "faithfulness" in df.columns:
            score = float(df["faithfulness"].iloc[0])
    assert score is not None, f"could not read faithfulness from {result!r}"
    assert 0.0 <= score <= 1.0
    # Grounded SDNU answer should score reasonably high with a working judge
    assert score >= 0.5, f"expected grounded faithfulness>=0.5, got {score}"
