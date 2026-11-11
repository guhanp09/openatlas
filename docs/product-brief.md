# Product brief

## Problem and intended user

A person seeking an explanation may prefer to ask and read in a language different from their device
settings. They also need enough context to judge a source while limiting unnecessary transfer.
OpenAtlas explores this workflow for English, Bengali and Telugu readers in a small knowledge collection.
This is a problem hypothesis supported by secondary research, not a finding from interviews conducted
for this project.

Google's [multilingual-search explanation](https://developers.google.com/search/blog/2023/09/multilingual-searches)
describes why search language cannot be reduced to device settings. Google Research's
[TyDi QA introduction](https://research.google/blog/tydi-qa-a-multilingual-question-answering-benchmark/)
motivates language-diverse information seeking. Neither source establishes demand for this prototype.

## User journey and success

Choose a language → ask a question → scan source previews → expand if needed → open the source.
The eventual user outcome is finding and understanding a useful source, not maximizing clicks.
Offline retrieval and byte measurements are proxies for only parts of that journey.

## Scope and prioritization

| Choice | Reason | Implemented acceptance evidence |
|---|---|---|
| Explicit language picker | Preserve reader control; avoid brittle language inference | Query results remain in the chosen collection; browser checks cover three scripts. |
| Source-first results | Let readers verify context without unvalidated answer generation | Title links and excerpts; unknown-vocabulary queries have an empty state. |
| Compact/expanded previews | Expose the context-versus-payload trade-off | Same ranked source IDs across modes; measured UTF-8 and compressed response sizes. |
| Per-language launch checks | Prevent a macro gain from masking language regression | Validation and evaluation report each language separately. |
| Local, sparse retrieval | Make the prototype runnable without credentials or remote inference | Hash-verified dataset download, local index, local server. |

Deferred: voice, automatic translation, generated answers, account synchronization and personalization.
These add dependencies and evaluation burdens before the basic find-and-read workflow is validated.
The small corpus is a deliberate prototype constraint; it cannot represent the open web.

## Requirements for a real pilot

- Native-language readers must be able to understand the controls and excerpts; UI chrome is currently English.
- Assess Telugu's remaining quality gap before broadening exposure.
- Evaluate whether shorter previews increase wrong source openings or repeated queries.
- Clarify attribution and privacy handling with appropriate reviewers before hosted deployment.
- Define a measurable successful-source task with an independent rubric and report failures.

The repository demonstrates problem framing, implementation, evaluation, prioritization and a staged
launch decision. Cross-functional reviewers and research participants are proposed in the launch plan;
none are claimed as collaborators already involved.
