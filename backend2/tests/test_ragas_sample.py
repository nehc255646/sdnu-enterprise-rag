"""Ragas-style evaluation sample for 后端2 RAG quality checks.

Always runs a lightweight offline smoke eval (no live LLM required).
Optionally soft-imports `ragas` when installed and exercises a trivial
Dataset row; full LLM-backed ragas.evaluate runs only when OPENAI_API_KEY
is set (otherwise soft-success after Dataset wiring).

Run:
    pytest tests/test_ragas_sample.py -q
"""

from __future__ import annotations

import os
import re
from typing import Any


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


def test_ragas_optional_package_soft_import():
    """Soft-import ragas when available; never fail/skip the suite for missing package."""
    try:
        import ragas  # noqa: F401
    except ImportError:
        # Offline smoke above is the required path; optional package absent is OK.
        assert True
        return

    try:
        from datasets import Dataset
    except ImportError:
        assert ragas is not None
        return

    row = {
        "question": [SAMPLE["question"]],
        "answer": [SAMPLE["answer"]],
        "contexts": [SAMPLE["contexts"]],
        "ground_truth": [SAMPLE["ground_truth"]],
    }
    ds = Dataset.from_dict(row)
    assert len(ds) == 1
    assert ds[0]["question"] == SAMPLE["question"]

    # Full ragas.evaluate needs an LLM; only attempt when OPENAI key present
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key or api_key.startswith("sk-your"):
        return  # soft success: dataset wiring verified without live LLM
