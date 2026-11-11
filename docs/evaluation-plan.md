# Evaluation plan

This plan specifies the comparison before the first evaluation run.

## Task and data

Use English, Bengali and Telugu records from the public TyDiQA-GoldP secondary-task release.
Convert them into a **derived closed-corpus passage retrieval task**, not the official TyDi QA
question-answering task. A query has one known relevant passage; other passages may also be relevant.
No answer generation or official leaderboard comparison is performed.

The official training split supplies at most 150 validation queries per language, selected by a stable
hash after removing duplicate questions and articles/questions shared with the official development split.
The official development questions are the final held-out evaluation set. Passage text from both splits
is searchable; questions and answer labels are never indexed. This is normal fixed-corpus retrieval:
held-out refers to the query/selection labels, not to hiding searchable documents from the index.

Include the selected validation and evaluation passages plus at most 800 background training passages
per language, deduplicated by normalized context. Report every count and the document IDs.
The corpus and labels are intentionally small and cannot support a web-scale search claim.

## Candidates and selection

Baseline: Unicode-aware word TF-IDF cosine similarity. Challenger: a weighted combination of word and
character 3–5-gram TF-IDF similarity. Fit vocabulary/IDF on the searchable passages only. Test character
weights 0, 0.25, 0.5, 0.75 and 1 on validation queries. Select a single global weight by language-macro
Recall@5, subject to no language falling more than 2 percentage points below the word baseline on
validation. Break ties in favor of lower character weight. Lock this choice before final evaluation.

## Outcomes and release decision

- Primary offline outcome: language-macro Recall@5 of the known relevant passage.
- Diagnostics: per-language Recall@1/5, MRR@10, paired query bootstrap intervals (2,000 draws,
  seed 2027), failures and the gap between languages.
- A pilot candidate must improve macro Recall@5 and avoid a point-estimate drop exceeding 2 pp in
  any language. This is a development gate, not a statistical non-inferiority proof or launch approval.
- Compare UTF-8 and gzip JSON response sizes for the same ranked results in compact and expanded
  modes. Report medians and paired mean byte reduction. Do not equate smaller responses with measured
  mobile speed, task success, or retention. Measure local warm-query latency separately.
- Publish unfavorable findings. No tuning after observing the held-out results.

## What comes after offline evaluation

A proposed moderated study with native-language readers would test findability, source comprehension,
keyboard use and the effect of shorter excerpts. No participants have been recruited or interviewed.
A later controlled pilot would measure successful source opening, reformulations and abandonment,
segmented by chosen language and data mode. Do not collect raw queries by default.
