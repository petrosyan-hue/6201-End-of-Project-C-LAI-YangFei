# 6201-End-of-Project-C-LAI-YangFei

## PE6201 End-of-Course Project

### AI Multilingual FAQ Assistant for Cross-Border E-commerce

This project builds a small multilingual FAQ assistant for cross-border e-commerce support. It retrieves the most relevant FAQ entry and answers in the user's language when possible. If the evidence is weak, it refuses to guess and asks the user to contact support.

## Why this project

Cross-border e-commerce customers may ask simple support questions in different languages. FAQ information is often scattered across policy pages, shipping pages and return pages, so customers may receive slow or inconsistent answers. A small retrieval-based assistant can make common support information easier to find while keeping answers grounded in approved FAQ records.

## What it does

- Reads a 50-entry simulated FAQ knowledge base from `data/faq.json`.
- Accepts English, Chinese or Spanish customer questions.
- Retrieves the best matching FAQ entry.
- Produces a short answer and cites the FAQ source.
- Refuses to answer when no FAQ entry is relevant enough.
- Records approximate tokens, latency and estimated cost.
- Runs an evaluation harness over 50 test cases in `eval/eval_cases.json`.
- Compares the assistant against a simple keyword baseline.
- Checks whether the answer language matches the customer's question language.
- Presents the workflow as a chat-widget style preview that could later be embedded in an e-commerce site.

## Product and explainer documentation

- Product documentation: `PRODUCT_DOCUMENTATION.md`
- Code documentation: `CODE_DOCUMENTATION.md`
- Data explainer: `data/README.md`
- Evaluation explainer: `eval/README.md`

## How to run from GitHub

Clone the repository, open the project folder, install the dependency, then run the web demo:

```bash
git clone https://github.com/petrosyan-hue/6201-End-of-Project-C-LAI-YangFei.git
cd 6201-End-of-Project-C-LAI-YangFei/PE6201-Ecommerce-FAQ-Assistant
python -m pip install -r requirements.txt
python -m streamlit run web_app.py
```

If you are using macOS and `python` does not work, use:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run web_app.py
```

If you do not use Git, you can also click `Code` → `Download ZIP`, unzip the project, open Terminal or PowerShell inside the `PE6201-Ecommerce-FAQ-Assistant` folder, and then run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run web_app.py
```

After Streamlit starts, open the local URL printed in the terminal, usually:

```text
http://localhost:8501
```

If another Streamlit app is already using port 8501, Streamlit may show another local URL such as:

```text
http://localhost:8502
```

Open the URL shown in the terminal.

If Streamlit asks for an email address on first launch, leave it blank and press Enter.

## How to run the command-line assistant

```bash
python app.py
```

On macOS, if `python` does not work, use:

```bash
python3 app.py
```

## How to run the evaluation harness

```bash
python eval/run_eval.py
```

On macOS, if `python` does not work, use:

```bash
python3 eval/run_eval.py
```

The evaluation prints assistant results, keyword baseline results, language match, average latency, token estimates and estimated cost.

## Example questions

```text
Where is my money after I sent the item back?
我的包裹丢了怎么办？
¿Dónde descargo la factura?
```

## Project structure

```text
.
├── app.py
├── web_app.py
├── src/
│   ├── assistant.py
│   ├── retrieval.py
│   └── metrics.py
├── data/
│   ├── faq.json
│   └── README.md
├── eval/
│   ├── eval_cases.json
│   ├── README.md
│   └── run_eval.py
├── README.md
├── PRODUCT_DOCUMENTATION.md
├── CODE_DOCUMENTATION.md
└── requirements.txt
```

## Notes

This first version uses deterministic local retrieval and template answers. It does not require an API key, so it can run on another machine without paid services.

The web demo is a standalone Streamlit prototype, not a production store plugin. In a real system, the same answer workflow could sit behind a small website chat widget or API endpoint.

If Streamlit asks for an email address on first launch, leave it blank and press Enter.

## Current measured result

The latest evaluation uses 50 scripted cases over 50 simulated FAQ entries:

```text
Assistant pass rate: 50/50 = 100%
Assistant source accuracy: 50/50 = 100%
Assistant content accuracy: 50/50 = 100%
Assistant language match: 50/50 = 100%
Assistant total estimated cost: $0.01555750

Keyword baseline pass rate: 33/50 = 66%
Keyword baseline source accuracy: 36/50 = 72%
Keyword baseline content accuracy: 33/50 = 66%
Keyword baseline language match: 50/50 = 100%
Keyword baseline total estimated cost: $0.01467000
```
```
