"""Pinned public data, deterministic sampling and query/article split isolation."""

import hashlib
import json
import unicodedata
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

LANGUAGES = {"english": "en", "bengali": "bn", "telugu": "te"}
REVISION = "da78f23f9119363459acbaf46bf89426ff26c259"
HASHES = {
    "train": "8139944554bcd89f6c4b167b93c9a63ec44a6d97b8caebe049061f78fcc0e786",
    "validation": "38760fbfc8fa4d0765026d56cfbb65a39231ad8cf5afef40f9c962a26bd3f94d",
}


def normalize(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def passage_id(language, context):
    return language + ":" + digest(normalize(context))[:24]


def download(root):
    raw = Path(root) / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    provenance = {
        "dataset": "TyDiQA-GoldP, Hugging Face secondary_task mirror",
        "revision": REVISION,
        "upstream": "https://github.com/google-research-datasets/tydiqa",
        "files": {},
    }
    for split, expected in HASHES.items():
        url = (
            "https://huggingface.co/datasets/google-research-datasets/tydiqa/resolve/"
            f"{REVISION}/secondary_task/{split}-00000-of-00001.parquet"
        )
        path = raw / f"{split}.parquet"
        if not path.exists():
            temporary = path.with_suffix(".download")
            urllib.request.urlretrieve(url, temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
                temporary.unlink()
                raise ValueError(f"Dataset integrity check failed: {split}")
            temporary.replace(path)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Dataset integrity check failed: {split}")
        provenance["files"][split] = {"url": url, "sha256": actual, "bytes": path.stat().st_size}
    (Path(root) / "data" / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return {split: pq.read_table(raw / f"{split}.parquet").to_pylist() for split in HASHES}


def prepare(train, development, validation_limit=150, background_limit=800):
    """Keep dev queries untouched by selection; remove train article/query overlaps."""
    documents, queries, counts = {}, {"validation": [], "evaluation": []}, {}

    def add_document(row, language):
        pid = passage_id(language, row["context"])
        documents.setdefault(
            pid,
            {
                "id": pid,
                "language": language,
                "title": row["title"],
                "context": unicodedata.normalize("NFC", row["context"]),
            },
        )
        return pid

    def unique_questions(rows):
        seen, result = set(), []
        for row in sorted(rows, key=lambda x: digest(x["id"])):
            key = normalize(row["question"])
            if key and key not in seen and normalize(row["context"]):
                seen.add(key)
                result.append(row)
        return result

    for language in LANGUAGES:
        raw_dev = [r for r in development if r["id"].startswith(language + "-")]
        raw_train = [r for r in train if r["id"].startswith(language + "-")]
        dev = unique_questions(raw_dev)
        dev_titles = {normalize(r["title"]) for r in raw_dev}
        dev_questions = {normalize(r["question"]) for r in raw_dev}
        isolated = [
            r
            for r in raw_train
            if normalize(r["title"]) not in dev_titles and normalize(r["question"]) not in dev_questions
        ]
        clean_train = unique_questions(isolated)
        selected = clean_train[:validation_limit]
        for split, rows in [("validation", selected), ("evaluation", dev)]:
            for row in rows:
                queries[split].append(
                    {
                        "id": row["id"],
                        "language": language,
                        "question": row["question"],
                        "gold": add_document(row, language),
                    }
                )
        # Background selection is context-based and independent of query relevance.
        background = {passage_id(language, r["context"]): r for r in clean_train[validation_limit:]}
        for pid in sorted(background)[:background_limit]:
            add_document(background[pid], language)
        counts[language] = {
            "source_train": len(raw_train),
            "source_development": len(raw_dev),
            "train_rows_removed_for_overlap": len(raw_train) - len(isolated),
            "development_duplicates_removed": len(raw_dev) - len(dev),
            "validation_queries": len(selected),
            "evaluation_queries": len(dev),
        }
    docs = sorted(documents.values(), key=lambda x: x["id"])
    for language in LANGUAGES:
        counts[language]["corpus_passages"] = sum(d["language"] == language for d in docs)
    return docs, queries, counts
