"""Command-line interface for the FAQ assistant.

This file is a minimal reproducible entry point for running the assistant
without the Streamlit UI. It is useful for quick manual checks and for showing
that the core retrieval-and-answer workflow is separate from the web demo.
"""

from pathlib import Path

from src.assistant import answer_question
from src.retrieval import load_faq


ROOT = Path(__file__).parent
FAQ_PATH = ROOT / "data" / "faq.json"


def main() -> None:
    entries = load_faq(FAQ_PATH)
    print("AI Multilingual FAQ Assistant for Cross-Border E-commerce")
    print("Type a question, or type 'quit' to exit.\n")
    while True:
        query = input("Question: ").strip()
        if query.lower() in {"quit", "exit", "q"}:
            break
        if not query:
            continue
        response = answer_question(query, entries)
        print("\nAnswer:")
        print(response.answer)
        print("\nEvidence:")
        print(f"source_id={response.source_id}, source={response.source_name}, confidence={response.confidence:.2f}")
        print("\nMetrics:")
        print(
            f"input_tokens={response.metrics.input_tokens}, "
            f"output_tokens={response.metrics.output_tokens}, "
            f"latency={response.metrics.latency_seconds:.4f}s, "
            f"estimated_cost=${response.metrics.estimated_cost_usd:.8f}"
        )
        print()


if __name__ == "__main__":
    main()
