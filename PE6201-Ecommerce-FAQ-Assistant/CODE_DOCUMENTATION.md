# Code Documentation

This file explains the main code modules at file level so the project can be scanned by a human reviewer or an AI agent without reading every line of code.

## app.py

Command-line entry point for the assistant. It loads the FAQ data, accepts a user question in the terminal, runs the assistant workflow, and prints the answer, retrieved source, confidence score, and run metrics.

## web_app.py

Streamlit web demo for the project. It handles the chat-style interface, topic shortcuts, mixed-language clarification, simulated order lookup, FAQ preview, uploaded screenshot placeholder, retrieval evidence panels, baseline comparison, evaluation results, and single-run token/cost metrics.

## src/assistant.py

Main assistant orchestration module. It decides whether a customer message should be answered from retrieved FAQ evidence, refused safely, or routed toward human support. It keeps answers grounded in approved FAQ records and records lightweight metrics for the coursework evaluation.

## src/retrieval.py

FAQ loading, language detection, tokenisation, scoring, and retrieval logic. It loads structured FAQ records, applies topic-keyword and phrase boosts, and returns the strongest FAQ record only when it passes the relevance threshold.

## src/metrics.py

Runtime metric helpers. It estimates input tokens, output tokens, latency, and simulated GPT-4o-based cost so the assistant can be compared with the keyword baseline.

## eval/run_eval.py

Evaluation runner. It runs the fixed 50-case test set against both the retrieval-grounded assistant and the keyword baseline, then reports pass rate, source accuracy, content accuracy, language match, latency, token estimates, and estimated cost.

## data/faq.json

Simulated 50-entry FAQ knowledge base used by the retrieval layer. It contains approved-style FAQ records across common cross-border e-commerce support topics.

## eval/eval_cases.json

Fixed 50-case evaluation set. Each case defines a customer question, expected FAQ source, required answer terms, and expected language behaviour.
