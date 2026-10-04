# Product Documentation

## Product name

AI Multilingual FAQ Assistant for Cross-Border E-commerce

## Persona

The primary user is a cross-border e-commerce customer who needs quick help with common support questions. The customer may use English, Chinese, Spanish, or natural wording that does not exactly match the store FAQ.

The secondary user is a support or operations team member who wants common FAQ answers to be consistent, source-grounded, and safe when the system does not know enough.

## Domain

Cross-border e-commerce customer service, focused on orders, delivery, returns, refunds, payments, invoices, account issues, and related FAQ support.

## Input

The system accepts:

- A customer support question in English, Chinese, or Spanish.
- A demo order number such as `SE-2026-002`.
- Optional demo evidence such as an uploaded order screenshot.
- A preferred response language when the customer message mixes languages.

## Output

The system returns:

- A short customer-facing answer.
- A FAQ source when the answer is grounded in FAQ retrieval.
- A safe refusal or human handoff message when the FAQ does not support an answer.
- A simulated order status response when the input is a demo order number.
- Coursework evidence panels showing retrieval candidates, baseline comparison, and single-run metrics.

## High-level architecture

```text
Customer question or order number
        |
        v
Streamlit web interface
        |
        +--> Order number? --> Simulated order lookup tool --> Order status answer
        |
        +--> Mixed-language? --> Ask user which language to answer in
        |
        +--> FAQ question --> Retrieval layer
                              |
                              v
                       50-entry FAQ database
                              |
                              v
                 Source-grounded assistant answer
                              |
                              v
             Evidence panel and evaluation metrics
```

## External intelligence and tools

The submitted prototype does not require a live paid LLM API. It uses deterministic local retrieval, language detection, template-style answers, and a simulated order lookup tool. A future version could connect to a hosted LLM API such as GPT-4o for more natural wording, but this would increase cost, latency, monitoring needs, and hallucination risk.

## Metrics targeted

- Assistant source accuracy.
- Assistant content accuracy.
- Assistant language match.
- Safe refusal for unsupported or sensitive questions.
- Comparison against a keyword baseline.
- Estimated token cost and latency.

## Metrics reached

Latest local evaluation:

- Assistant pass rate: 50/50, 100%.
- Assistant source accuracy: 50/50, 100%.
- Assistant content accuracy: 50/50, 100%.
- Assistant language match: 50/50, 100%.
- Keyword baseline pass rate: 33/50, 66%.
- Keyword baseline source accuracy: 36/50, 72%.
- Assistant estimated cost for 50 cases: USD 0.01555750.
- Keyword baseline estimated cost for 50 cases: USD 0.01467000.

## Minimum viable model

The minimum viable model is a bounded retrieval-grounded FAQ assistant: it loads a small approved FAQ dataset, retrieves the most relevant record, answers only from that record, refuses unsupported questions, and records evaluation metrics. The simulated order lookup is an extra demo tool that shows how a future assistant could connect to read-only operational systems.

## Rough edges and future work

- The FAQ and order records are simulated, not live business data.
- The evaluation set is fixed and may not represent all real customer phrasing.
- Mixed-language handling is conservative and asks for a preferred answer language.
- The prototype does not execute real actions such as refunds, address changes, or payment checks.
- A production version should use a reviewed help-centre dataset, authenticated order tools, logging, human handoff, and broader evaluation with real anonymised support questions.
