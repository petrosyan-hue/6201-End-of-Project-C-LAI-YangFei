"""Answer orchestration for the multilingual FAQ assistant.

This module decides whether a customer message should be answered from retrieved
FAQ evidence, refused safely, or routed toward human support. It keeps the
customer-facing answer grounded in approved FAQ records and records lightweight
run metrics for the coursework evaluation.
"""

from dataclasses import dataclass

from .metrics import RunMetrics, estimate_cost, estimate_tokens, timer
from .retrieval import FAQEntry, detect_language, retrieve


@dataclass
class AssistantResponse:
    answer: str
    source_id: str | None
    source_name: str | None
    confidence: float
    metrics: RunMetrics


SENSITIVE_OR_UNSUPPORTED_PATTERNS = {
    "access my bank card",
    "bank card",
    "credit card number",
    "real refund status",
    "live refund status",
    "exact refund status",
    "my exact refund",
    "recommend the best",
    "best laptop",
    "gaming laptop",
}


def should_handoff(query: str) -> bool:
    lowered = query.lower()
    return any(pattern in lowered for pattern in SENSITIVE_OR_UNSUPPORTED_PATTERNS)


def language_clarification() -> str:
    return (
        "I detected mixed languages. Should I continue answering you in English, Chinese, or Spanish?"
    )


def refusal(language: str) -> str:
    if language == "mixed":
        return language_clarification()
    if language == "zh":
        return "我无法从现有FAQ中可靠回答这个问题。请联系人工客服。转人工客服。"
    if language == "es":
        return "No puedo responder de forma fiable con la FAQ disponible. Contacta con soporte. Derivar a soporte humano."
    return "I cannot answer this reliably from the available FAQ. Please contact customer support. Route to human support."


def format_answer(query: str, entry: FAQEntry | None, confidence: float) -> str:
    language = detect_language(query)
    if entry is None:
        return refusal(language)
    if language == "zh":
        return f"{entry.answer}（来源：{entry.source}）"
    if language == "es" and entry.language == "es":
        return f"{entry.answer} Fuente: {entry.source}."
    return f"{entry.answer} Source: {entry.source}."


def answer_question(query: str, entries: list[FAQEntry]) -> AssistantResponse:
    with timer() as elapsed:
        if detect_language(query) == "mixed" or should_handoff(query):
            entry, confidence = None, 0.0
        else:
            entry, confidence = retrieve(query, entries)
        answer = format_answer(query, entry, confidence)
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
    return AssistantResponse(
        answer=answer,
        source_id=entry.id if entry else None,
        source_name=entry.source if entry else None,
        confidence=confidence,
        metrics=metrics,
    )
