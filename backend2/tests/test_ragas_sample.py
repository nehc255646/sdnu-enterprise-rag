"""Minimal Ragas evaluation sample for 后端2 RAG quality checks.

This test documents the Ragas eval path. It is skippable when `ragas` is not
installed (`pytest.importorskip`). With ragas present, it runs a trivial
faithfulness-style assertion on a stubbed single-turn sample (no live LLM).

Install (optional):
    pip install ragas datasets

Run:
    pytest tests/test_ragas_sample.py -q
"""

from __future__ import annotations

import pytest

ragas = pytest.importorskip("ragas", reason="ragas not installed; sample documents eval path only")


def test_ragas_sample_stub_metrics():
    """Trivial sample: when ragas is available, validate a hand-crafted row.

    Full pipeline wiring (retrieve → answer → ragas.evaluate) lives outside this
    stub; this asserts the eval package imports and a dummy score stays in [0, 1].
    """
    # Prefer evaluating with Dataset if available; otherwise assert import + stub score.
    sample = {
        "question": "What stack does Alice use?",
        "answer": "Alice uses Python and FastAPI.",
        "contexts": ["Alice resume: Python FastAPI"],
        "ground_truth": "Python FastAPI",
    }
    # Stub metric: answer tokens overlap with context (stand-in for faithfulness)
    ctx = " ".join(sample["contexts"]).lower()
    ans_tokens = set(sample["answer"].lower().split())
    overlap = sum(1 for t in ans_tokens if t in ctx) / max(len(ans_tokens), 1)
    assert 0.0 <= overlap <= 1.0
    assert overlap > 0.0, "stub faithfulness-like score should be positive for grounded answer"
    assert ragas is not None
