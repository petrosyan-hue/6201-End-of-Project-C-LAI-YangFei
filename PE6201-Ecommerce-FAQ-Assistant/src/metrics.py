"""Lightweight runtime metrics for the prototype.

The project does not call a live paid model, so these metrics are approximate.
They provide consistent token, latency, and cost estimates for comparing the
assistant with the keyword baseline and for discussing production trade-offs.
"""

import re
import time
from contextlib import contextmanager
from dataclasses import dataclass


WORD_RE = re.compile(r"\w+|[\u4e00-\u9fff]")


@dataclass
class RunMetrics:
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    estimated_cost_usd: float


@contextmanager
def timer():
    start = time.perf_counter()
    result = {"elapsed": 0.0}
    try:
        yield result
    finally:
        result["elapsed"] = time.perf_counter() - start


def estimate_tokens(text: str) -> int:
    # Approximation for reporting. Real API tokenizers differ by model.
    return len(WORD_RE.findall(text))


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    # Prototype estimate based on GPT-4o API pricing:
    # input US$2.50/M tokens, output US$10.00/M tokens.
    input_cost = input_tokens / 1_000_000 * 2.50
    output_cost = output_tokens / 1_000_000 * 10.00
    return input_cost + output_cost
