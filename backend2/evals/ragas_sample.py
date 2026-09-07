"""Pointer: Ragas-style sample lives at tests/test_ragas_sample.py.

Offline smoke always runs (no live LLM). Optional ragas soft-import when installed.

Run: pytest tests/test_ragas_sample.py -q
"""

from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[1] / "tests" / "test_ragas_sample.py"

if __name__ == "__main__":
    print(f"Ragas sample: {SAMPLE}")
    print("Run: pytest tests/test_ragas_sample.py -q")
