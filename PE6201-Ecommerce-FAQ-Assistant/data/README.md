# Data Explainer

## Dataset

The prototype uses `faq.json` as its local FAQ knowledge base.

## What the data represents

The file contains 50 simulated FAQ records for cross-border e-commerce customer support. The topics include returns, refunds, delivery, lost packages, cancellation, customs, payment, warranty, account access, invoices, privacy, and product authenticity.

## Why simulated data is used

The project does not use real customer records, real order data, personal data, payment data, or private store information. The FAQ records are carefully written simulated examples so the prototype can demonstrate retrieval, multilingual answering, refusal, and evaluation without privacy risk.

## Schema

Each FAQ record contains:

- `id`: stable FAQ identifier used by retrieval and evaluation.
- `topic`: support category used for scoring and explanation.
- `language`: FAQ language marker.
- `question`: representative customer question.
- `answer`: approved answer text used by the assistant.
- `source`: policy/source label shown in the response.

## Data constraints

This is not a production help-centre dataset. It is sufficient for a coursework prototype and transparent evaluation, but a real deployment would need an approved live help-centre dataset, owner review, and ongoing updates.
