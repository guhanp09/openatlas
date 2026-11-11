"""Validation-only selection followed by fixed held-out retrieval and payload evaluation."""

import csv
import gzip
import json
import platform
import time
from pathlib import Path

import joblib
import matplotlib
import numpy as np

from .data import LANGUAGES, download, prepare
from .search import SearchIndex, encode, response

matplotlib.use("Agg")
import matplotlib.pyplot as plt

WEIGHTS = [0, 0.25, 0.5, 0.75, 1]


def ranks_for(scores, gold_positions):
    """Stable tie policy matches production ranking; zero-score gold is not retrieved."""
    order = np.argsort(-scores, axis=1, kind="stable")
    result = []
    for i, gold in enumerate(gold_positions):
        result.append(int(np.flatnonzero(order[i] == gold)[0]) + 1 if scores[i, gold] > 0 else 10**9)
    return np.array(result)


def metrics(ranks):
    ranks = np.asarray(ranks)
    return {
        "queries": len(ranks),
        "recall_at_1": float(np.mean(ranks <= 1)),
        "recall_at_5": float(np.mean(ranks <= 5)),
        "mrr_at_10": float(np.mean(np.where(ranks <= 10, 1 / ranks, 0))),
    }


def choose_weight(validation):
    baseline = validation[0]
    eligible = [
        w
        for w in WEIGHTS
        if all(
            validation[w][lang]["recall_at_5"] >= baseline[lang]["recall_at_5"] - 0.02 for lang in LANGUAGES
        )
    ]
    return max(
        eligible, key=lambda w: (np.mean([validation[w][lang]["recall_at_5"] for lang in LANGUAGES]), -w)
    )


def paired_interval(baseline, challenger, seed=2027, draws=2000):
    difference = (np.asarray(challenger) <= 5).astype(float) - (np.asarray(baseline) <= 5)
    rng = np.random.default_rng(seed)
    means = difference[rng.integers(0, len(difference), (draws, len(difference)))].mean(axis=1)
    return {
        "difference": float(difference.mean()),
        "lower_95": float(np.quantile(means, 0.025)),
        "upper_95": float(np.quantile(means, 0.975)),
        "unit": "query",
        "draws": draws,
    }


def write_csv(path, rows):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def evaluate(root):
    root = Path(root)
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    source = download(root)
    docs, queries, counts = prepare(source["train"], source["validation"])
    index = SearchIndex(docs)
    validation, cached = {w: {} for w in WEIGHTS}, {}
    for language in LANGUAGES:
        positions = {d["id"]: i for i, d in enumerate(index.parts[language]["documents"])}
        val = [q for q in queries["validation"] if q["language"] == language]
        word, char = index.score_batch([q["question"] for q in val], language)
        gold = [positions[q["gold"]] for q in val]
        for weight in WEIGHTS:
            validation[weight][language] = metrics(ranks_for((1 - weight) * word + weight * char, gold))
        cached[language] = positions
    weight = choose_weight(validation)
    # Persist the locked policy before computing evaluation outcomes.
    policy = {
        "character_weight": weight,
        "selection": "validation_language_macro_recall_at_5",
        "guardrail": "no validation language decline greater than 0.02",
        "validation": validation,
    }
    (reports / "selection.json").write_text(json.dumps(policy, indent=2) + "\n")
    results, predictions, payloads, timings = {}, [], [], []
    for language in LANGUAGES:
        rows = [q for q in queries["evaluation"] if q["language"] == language]
        word, char = index.score_batch([q["question"] for q in rows], language)
        gold = [cached[language][q["gold"]] for q in rows]
        baseline = ranks_for(word, gold)
        selected = ranks_for((1 - weight) * word + weight * char, gold)
        results[language] = {
            "baseline": metrics(baseline),
            "selected": metrics(selected),
            "paired_recall5": paired_interval(baseline, selected),
        }
        for q, before, after in zip(rows, baseline, selected):
            predictions.append(
                {
                    "id": q["id"],
                    "language": language,
                    "gold_passage": q["gold"],
                    "baseline_rank": int(before),
                    "selected_rank": int(after),
                }
            )
        # Measure every evaluation response. Rank timing excludes download/index build/browser/network.
        for q in rows:
            start = time.perf_counter()
            ranked = index.rank(q["question"], language, weight)
            timings.append((time.perf_counter() - start) * 1000)
            compact = encode(response(ranked, language, "compact"))
            expanded = encode(response(ranked, language, "expanded"))
            payloads.append(
                {
                    "id": q["id"],
                    "language": language,
                    "compact_bytes": len(compact),
                    "expanded_bytes": len(expanded),
                    "compact_gzip_bytes": len(gzip.compress(compact)),
                    "expanded_gzip_bytes": len(gzip.compress(expanded)),
                }
            )
    macro_before = float(np.mean([r["baseline"]["recall_at_5"] for r in results.values()]))
    macro_after = float(np.mean([r["selected"]["recall_at_5"] for r in results.values()]))
    guardrail = all(r["paired_recall5"]["difference"] >= -0.02 for r in results.values())
    payload_summary = {
        key: float(np.median([p[key] for p in payloads]))
        for key in ["compact_bytes", "expanded_bytes", "compact_gzip_bytes", "expanded_gzip_bytes"]
    }
    for prefix in ["", "gzip_"]:
        compact = np.array([p[f"compact_{prefix}bytes"] for p in payloads])
        expanded = np.array([p[f"expanded_{prefix}bytes"] for p in payloads])
        payload_summary[f"mean_paired_{prefix}reduction"] = float(np.mean(1 - compact / expanded))
    summary = {
        "task": "derived closed-corpus retrieval; not an official TyDi QA score",
        "languages": results,
        "counts": counts,
        "passages": len(docs),
        "validation_queries": len(queries["validation"]),
        "evaluation_queries": len(predictions),
        "selected_character_weight": weight,
        "macro_recall5_baseline": macro_before,
        "macro_recall5_selected": macro_after,
        "language_guardrail_pass": guardrail,
        "decision": "REVIEWED_PILOT_CANDIDATE"
        if guardrail and macro_after > macro_before
        else "ITERATE_BEFORE_PILOT",
        "payload": payload_summary,
        "local_timing": {
            "platform": platform.platform(),
            "warm_query_p50_ms": float(np.median(timings)),
            "warm_query_p95_ms": float(np.quantile(timings, 0.95)),
        },
    }
    (reports / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_csv(reports / "predictions.csv", predictions)
    write_csv(reports / "payloads.csv", payloads)
    write_csv(reports / "corpus_manifest.csv", [{"id": d["id"], "language": d["language"]} for d in docs])
    (root / "models").mkdir(exist_ok=True)
    # Artifact is local only. Never load untrusted joblib files.
    joblib.dump({"index": index, "weight": weight}, root / "models" / "search.joblib", compress=3)
    examples = {
        lang: next(q["question"] for q in queries["validation"] if q["language"] == lang)
        for lang in LANGUAGES
    }
    (root / "models" / "examples.json").write_text(json.dumps(examples, ensure_ascii=False))
    lines = [
        "# Search quality and launch decision",
        "",
        f"**{summary['decision']}**",
        "",
        "Derived closed-corpus retrieval on TyDiQA-GoldP passages; not the official QA task.",
        "",
        (
            f"{len(docs):,} passages; {len(queries['validation'])} validation queries; "
            f"{len(predictions):,} held-out development queries. Locked character weight: {weight}."
        ),
        "",
        "| Language | Word Recall@5 | Selected Recall@5 | Paired change (95% query bootstrap) |",
        "|---|---:|---:|---:|",
    ]
    for lang, r in results.items():
        ci = r["paired_recall5"]
        lines.append(
            f"| {lang.title()} | {r['baseline']['recall_at_5']:.1%} | "
            f"{r['selected']['recall_at_5']:.1%} | {100 * ci['difference']:+.1f} pp "
            f"[{100 * ci['lower_95']:+.1f}, {100 * ci['upper_95']:+.1f}] |"
        )
    lines += [
        "",
        f"Equal-language macro Recall@5: **{macro_before:.1%} → {macro_after:.1%}**.",
        "",
        (
            f"Compact mode reduces paired UTF-8 JSON response size by "
            f"**{payload_summary['mean_paired_reduction']:.1%}** on average; gzip reduction is "
            f"**{payload_summary['mean_paired_gzip_reduction']:.1%}**. Ranked IDs are unchanged."
        ),
        "",
        "## Product interpretation",
        "",
        (
            "A quality gain supports a moderated pilot, not broad release. Native-reader usability, "
            "snippet comprehension, transliterated/code-switched queries and actual mobile performance "
            "remain unmeasured. The compact view may hide useful context; expansion stays available."
        ),
        "",
        (
            "The gate uses point estimates and is not a statistical non-inferiority claim. Bootstrap "
            "intervals resample queries and do not model article clustering or corpus uncertainty. "
            "The selected corpus guarantees a known relevant passage, unlike open-web search. "
            "No answerability or out-of-domain accuracy is claimed."
        ),
        "",
        (
            "All query-level ranks are in predictions.csv. Rank 1000000000 means zero lexical overlap. "
            "Raw questions/passages stay in ignored local files; public reports contain IDs and metrics."
        ),
    ]
    (reports / "decision.md").write_text("\n".join(lines) + "\n")
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 11})
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = np.arange(len(LANGUAGES))
    ax.bar(
        x - 0.18,
        [r["baseline"]["recall_at_5"] for r in results.values()],
        0.34,
        label="Word baseline",
        color="#b4c4cf",
    )
    ax.bar(
        x + 0.18,
        [r["selected"]["recall_at_5"] for r in results.values()],
        0.34,
        label="Validation-selected blend",
        color="#00796f",
    )
    ax.set(
        xticks=x,
        xticklabels=[x.title() for x in LANGUAGES],
        ylim=(0, 1),
        ylabel="Known relevant passage in top 5",
        title="Search quality, checked in each language",
    )
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(
        0.02,
        0.01,
        "Derived closed-corpus task • held-out queries • no production or official QA claim",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(reports / "quality.png", dpi=160)
    plt.close(fig)
    return summary
