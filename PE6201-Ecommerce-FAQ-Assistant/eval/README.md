# Evaluation Explainer

## Purpose

The evaluation checks whether the assistant answers from the expected FAQ evidence and whether it behaves safely when the FAQ does not support an answer.

## Files

- `eval_cases.json`: fixed test set used for evaluation.
- `run_eval.py`: evaluation runner.
- `eval_results.json`: detailed output from the latest run.

## Test case schema

Each case includes:

- `id`: test case identifier.
- `question`: customer question.
- `expected_source_id`: expected FAQ source, or `null` for unsupported cases.
- `must_contain`: terms that should appear in a correct answer.
- `expected_language`: expected response language or refusal behaviour.

## Metrics targeted

The project targets:

- Source accuracy: the assistant should retrieve the expected FAQ source.
- Content accuracy: the answer should include required policy terms.
- Language match: the answer should match the expected language behaviour.
- Safe refusal: unsupported or sensitive questions should not be guessed.
- Baseline comparison: the assistant should outperform a simple keyword baseline.

## Latest measured results

The latest local evaluation uses 50 test cases.

- Assistant pass rate: 50/50, 100%.
- Assistant language match: 50/50, 100%.
- Keyword baseline pass rate: 33/50, 66%.
- Keyword baseline source accuracy: 36/50, 72%.

## Critique

The evaluation is transparent and repeatable, but it is still simulated. It does not prove production performance on messy real customer messages, spelling mistakes, adversarial inputs, or a changing live FAQ. A future version should add real anonymised support questions, broader mixed-language cases, and human review of borderline failures.
