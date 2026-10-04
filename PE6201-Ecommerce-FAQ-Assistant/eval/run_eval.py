"""Evaluation runner for the coursework prototype.

This module runs the same fixed test set against the retrieval-grounded
assistant and a simple keyword baseline. It reports source accuracy, content
accuracy, language match, latency, token estimates, and simulated GPT-4o-based
cost so the project can compare AI value against a transparent baseline.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.assistant import answer_question
from src.metrics import RunMetrics, estimate_cost, estimate_tokens, timer
from src.retrieval import FAQEntry, detect_language, load_faq, retrieve, tokenize


def contains_all(answer: str, expected_terms: list[str]) -> bool:
    lowered = answer.lower()
    return all(term.lower() in lowered for term in expected_terms)


def language_matches(answer: str, expected_language: str) -> bool:
    if expected_language == "zh":
        return any("\u4e00" <= char <= "\u9fff" for char in answer)
    if expected_language == "es":
        spanish_markers = {
            " el ", " la ", " los ", " las ", " del ", " de ", " días", "envío",
            "pedido", "cliente", "tarjetas", "garantía", "reembolso", "soporte"
        }
        lowered = f" {answer.lower()} "
        return any(marker in lowered for marker in spanish_markers)
    return not any("\u4e00" <= char <= "\u9fff" for char in answer)


def keyword_baseline_retrieve(query: str, entries: list[FAQEntry]) -> tuple[FAQEntry | None, float]:
    """Simple comparison baseline: word overlap only, no topic boosts or language preference."""
    if detect_language(query) == "mixed":
        return None, 0.0
    query_terms = tokenize(query)
    if not query_terms:
        return None, 0.0
    scored = []
    for entry in entries:
        entry_terms = tokenize(f"{entry.question} {entry.answer}")
        score = len(query_terms & entry_terms) / len(query_terms)
        scored.append((score, entry))
    scored.sort(reverse=True, key=lambda item: item[0])
    if not scored or scored[0][0] < 0.18:
        return None, scored[0][0] if scored else 0.0
    return scored[0][1], scored[0][0]


def format_baseline_answer(query: str, entry: FAQEntry | None) -> str:
    language = detect_language(query)
    if entry is None:
        if language == "zh":
            return "我无法从现有FAQ中可靠回答这个问题。请联系人工客服。"
        if language == "es":
            return "No puedo responder de forma fiable con la FAQ disponible. Contacta con soporte."
        return "I cannot answer this reliably from the available FAQ. Please contact customer support."
    if language == "zh":
        return f"{entry.answer}（来源：{entry.source}）"
    if language == "es" and entry.language == "es":
        return f"{entry.answer} Fuente: {entry.source}."
    return f"{entry.answer} Source: {entry.source}."


def answer_keyword_baseline(query: str, entries: list[FAQEntry]):
    with timer() as elapsed:
        entry, confidence = keyword_baseline_retrieve(query, entries)
        answer = format_baseline_answer(query, entry)
    input_text = query
    if entry:
        input_text += " " + entry.question + " " + entry.answer
    input_tokens = estimate_tokens(input_text)
    output_tokens = estimate_tokens(answer)
    metrics = RunMetrics(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_seconds=elapsed["elapsed"],
        estimated_cost_usd=estimate_cost(input_tokens, output_tokens),
    )
    return {
        "answer": answer,
        "source_id": entry.id if entry else None,
        "confidence": confidence,
        "metrics": metrics,
    }


def summarize(label: str, results: list[dict]) -> None:
    passed_count = sum(1 for result in results if result["passed"])
    source_count = sum(1 for result in results if result["source_ok"])
    content_count = sum(1 for result in results if result["content_ok"])
    language_count = sum(1 for result in results if result["language_ok"])
    total_latency = sum(result["latency_seconds"] for result in results)
    total_input_tokens = sum(result["input_tokens"] for result in results)
    total_output_tokens = sum(result["output_tokens"] for result in results)
    total_cost = sum(result["estimated_cost_usd"] for result in results)

    print(f"{label} pass rate: {passed_count}/{len(results)} = {passed_count / len(results):.0%}")
    print(f"{label} source accuracy: {source_count}/{len(results)} = {source_count / len(results):.0%}")
    print(f"{label} content accuracy: {content_count}/{len(results)} = {content_count / len(results):.0%}")
    print(f"{label} language match: {language_count}/{len(results)} = {language_count / len(results):.0%}")
    print(f"{label} average latency: {total_latency / len(results):.4f}s")
    print(f"{label} average input tokens: {total_input_tokens / len(results):.1f}")
    print(f"{label} average output tokens: {total_output_tokens / len(results):.1f}")
    print(f"{label} total estimated cost: ${total_cost:.8f}")


def main() -> None:
    entries = load_faq(ROOT / "data" / "faq.json")
    cases = json.loads((ROOT / "eval" / "eval_cases.json").read_text(encoding="utf-8"))
    assistant_results = []
    baseline_results = []

    for case in cases:
        response = answer_question(case["question"], entries)
        source_ok = response.source_id == case["expected_source_id"]
        content_ok = contains_all(response.answer, case["must_contain"])
        language_ok = language_matches(response.answer, case["expected_language"])
        passed = source_ok and content_ok and language_ok
        assistant_results.append(
            {
                "id": case["id"],
                "passed": passed,
                "source_ok": source_ok,
                "content_ok": content_ok,
                "language_ok": language_ok,
                "expected_language": case["expected_language"],
                "expected_source_id": case["expected_source_id"],
                "actual_source_id": response.source_id,
                "answer": response.answer,
                "latency_seconds": response.metrics.latency_seconds,
                "input_tokens": response.metrics.input_tokens,
                "output_tokens": response.metrics.output_tokens,
                "estimated_cost_usd": response.metrics.estimated_cost_usd,
            }
        )

        baseline = answer_keyword_baseline(case["question"], entries)
        baseline_source_ok = baseline["source_id"] == case["expected_source_id"]
        baseline_content_ok = contains_all(baseline["answer"], case["must_contain"])
        baseline_language_ok = language_matches(baseline["answer"], case["expected_language"])
        baseline_passed = baseline_source_ok and baseline_content_ok and baseline_language_ok
        baseline_results.append(
            {
                "id": case["id"],
                "passed": baseline_passed,
                "source_ok": baseline_source_ok,
                "content_ok": baseline_content_ok,
                "language_ok": baseline_language_ok,
                "expected_language": case["expected_language"],
                "expected_source_id": case["expected_source_id"],
                "actual_source_id": baseline["source_id"],
                "answer": baseline["answer"],
                "latency_seconds": baseline["metrics"].latency_seconds,
                "input_tokens": baseline["metrics"].input_tokens,
                "output_tokens": baseline["metrics"].output_tokens,
                "estimated_cost_usd": baseline["metrics"].estimated_cost_usd,
            }
        )

    summarize("Assistant", assistant_results)
    print()
    summarize("Keyword baseline", baseline_results)
    print()
    for result in assistant_results:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"{status} {result['id']}: expected={result['expected_source_id']} "
            f"actual={result['actual_source_id']} language_ok={result['language_ok']}"
        )

    output_path = ROOT / "eval" / "eval_results.json"
    output_path.write_text(
        json.dumps(
            {
                "assistant": assistant_results,
                "keyword_baseline": baseline_results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nSaved detailed results to {output_path}")


if __name__ == "__main__":
    main()
