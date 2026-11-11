# Search quality and launch decision

**REVIEWED_PILOT_CANDIDATE**

Derived closed-corpus retrieval on TyDiQA-GoldP passages; not the official QA task.

3,931 passages; 450 validation queries; 1,222 held-out development queries. Locked character weight: 0.75.

| Language | Word Recall@5 | Selected Recall@5 | Paired change (95% query bootstrap) |
|---|---:|---:|---:|
| English | 88.0% | 92.5% | +4.5 pp [+1.8, +7.3] |
| Bengali | 69.9% | 92.0% | +22.1 pp [+15.0, +30.1] |
| Telugu | 71.7% | 75.5% | +3.7 pp [+1.0, +6.4] |

Equal-language macro Recall@5: **76.5% → 86.7%**.

Compact mode reduces paired UTF-8 JSON response size by **39.8%** on average; gzip reduction is **35.0%**. Ranked IDs are unchanged.

## Product interpretation

A quality gain supports a moderated pilot, not broad release. Native-reader usability, snippet comprehension, transliterated/code-switched queries and actual mobile performance remain unmeasured. The compact view may hide useful context; expansion stays available.

The gate uses point estimates and is not a statistical non-inferiority claim. Bootstrap intervals resample queries and do not model article clustering or corpus uncertainty. The selected corpus guarantees a known relevant passage, unlike open-web search. No answerability or out-of-domain accuracy is claimed.

All query-level ranks are in predictions.csv. Rank 1000000000 means zero lexical overlap. Raw questions/passages stay in ignored local files; public reports contain IDs and metrics.
