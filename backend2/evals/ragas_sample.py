"""Pointer: Ragas sample lives at tests/test_ragas_sample.py.

- Offline smoke: always runs (no live LLM).
- Live: `test_ragas_evaluate_live_ollama` calls real `ragas.evaluate` against
  local Ollama OpenAI-compat (`http://127.0.0.1:11434/v1`, model qwen2.5:1.5b).
  Skips only when Ollama/model unreachable.

Deps: see requirements.txt (`ragas`, `datasets`) or `pip install -r requirements-eval.txt`.

Run: pytest tests/test_ragas_sample.py -q
"""

from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[1] / "tests" / "test_ragas_sample.py"

if __name__ == "__main__":
    print(f"Ragas sample: {SAMPLE}")
    print("Run: pytest tests/test_ragas_sample.py -q")
