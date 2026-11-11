# Proposed research and launch plan

These are next steps, not completed user studies or business outcomes.

## Stage 1: moderated prototype research

Recruit readers who normally search in each supported language. Start with a small exploratory group
per language; this would be qualitative issue discovery, not a representative performance estimate.
Include mobile and keyboard use. Ask participants to find and explain a source for a task they care about,
then compare compact and expanded previews with task order counterbalanced.

Observe source comprehension, reformulations, wrong-language expectations, incomplete snippets and
navigation failures. Ask permission before recording. Avoid sensitive queries; store anonymized issue
notes rather than complete personal search histories. No such participants have yet been recruited.

## Stage 2: fix the largest blockers

Investigate Telugu failures by query type with native-language help; distinguish tokenization, morphology,
corpus coverage and question interpretation. Trial better retrieval only on a new validation partition.
The current held-out results are now observed and must not become a repeated tuning target presented
as fresh evidence. Localize interface controls after checking terminology with readers.

## Stage 3: controlled pilot

Randomize preview mode at the consenting-user level to avoid assigning the same reader inconsistent
experiences. Primary outcome: successful source task completion, assessed with a defined rubric.
Guardrails: comprehension errors, abandonment, repeated-query rate, source-opening failures and the
lowest-performing language. Response bytes and on-device load timing are secondary operational measures.

Use pilot baseline rates to plan sample size and a practically useful effect before opening the experiment.
Specify a fixed horizon and language-level reporting. Do not stop when a favorable number first appears.
Use the existing FirstMile-style validity/guardrail principles, adapted to this task's outcome definition.

## Proposed review responsibilities

| Review area | Decision needed before public deployment |
|---|---|
| Product / research | Validate the user problem, task rubric, scope and success criteria. |
| Engineering | Check indexing, latency, failure states, recovery and reproducibility. |
| UX / accessibility / language specialists | Check language controls, reading comprehension, keyboard and assistive-technology behavior. |
| Privacy / legal | Review collection consent, telemetry minimization and source attribution. |
| Launch communications | Describe supported languages and bounded collection accurately; avoid implying official Google affiliation. |

No named team or collaboration is asserted. This plan makes dependencies reviewable for a future pilot.
