"""Unicode-aware sparse retrieval and byte-conscious source previews."""

import json
import unicodedata
from urllib.parse import quote

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from .data import LANGUAGES, normalize


def select_terms(terms, frequencies, limit):
    """Resolve frequency ties lexically, independent of NumPy's platform-specific quicksort."""
    selected = sorted(zip(terms, frequencies), key=lambda item: (-int(item[1]), item[0]))[:limit]
    return {term: i for i, term in enumerate(sorted(term for term, _ in selected))}


def ranking_order(scores):
    """Resolve insignificant floating point differences with a shared, stable rank policy."""
    return np.argsort(-np.round(scores, 12), axis=-1, kind="stable")


def words(text):
    """Preserve combining marks in Indic scripts rather than splitting at vowel signs."""
    tokens, current = [], []
    for char in normalize(text):
        if unicodedata.category(char)[0] in {"L", "M", "N"}:
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def truncate(text, limit):
    """Do not begin a trailing fragment with a detached combining mark."""
    if len(text) <= limit:
        return text
    end = limit
    while end < len(text) and (
        unicodedata.category(text[end]).startswith("M") or text[end] in {"\u200d", "\u200c"}
    ):
        end += 1
    # Keep the next letter if a virama/joiner links a conjunct at this boundary.
    while end < len(text) and (
        unicodedata.combining(text[end - 1]) == 9 or text[end - 1] in {"\u200d", "\u200c"}
    ):
        end += 1
        while end < len(text) and unicodedata.category(text[end]).startswith("M"):
            end += 1
    return text[:end].rstrip() + "…"


class SearchIndex:
    def __init__(self, documents):
        self.parts = {}
        for language in LANGUAGES:
            docs = sorted([d for d in documents if d["language"] == language], key=lambda d: d["id"])
            if not docs:
                continue
            # Context only: do not index benchmark questions, answers, or IDs.
            contexts = [d["context"] for d in docs]
            word = TfidfVectorizer(
                tokenizer=words,
                token_pattern=None,
                lowercase=False,
                ngram_range=(1, 2),
                sublinear_tf=True,
                dtype=np.float64,
            )
            # The default max_features implementation uses an unstable frequency sort.
            # Select the same bounded vocabulary on every platform before fitting IDF.
            counter = CountVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                lowercase=False,
                preprocessor=normalize,
                dtype=np.int64,
            )
            counts = counter.fit_transform(contexts)
            vocabulary = select_terms(
                counter.get_feature_names_out(), np.asarray(counts.sum(axis=0)).ravel(), 120000
            )
            char = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                lowercase=False,
                preprocessor=normalize,
                sublinear_tf=True,
                vocabulary=vocabulary,
                dtype=np.float64,
            )
            self.parts[language] = {
                "documents": docs,
                "word": word,
                "char": char,
                "word_matrix": word.fit_transform(contexts),
                "char_matrix": char.fit_transform(contexts),
            }

    def score_batch(self, questions, language):
        part = self.parts[language]
        return tuple(
            (part[k].transform(questions) @ part[k + "_matrix"].T).toarray() for k in ["word", "char"]
        )

    def rank(self, question, language, weight, k=5):
        if language not in self.parts:
            raise ValueError("Choose English, Bengali or Telugu.")
        if not isinstance(question, str) or not question.strip():
            return []
        if len(question) > 300:
            raise ValueError("Keep the question within 300 characters.")
        if not 0 <= weight <= 1 or not 1 <= k <= 10:
            raise ValueError("Invalid retrieval settings.")
        word, char = self.score_batch([question], language)
        scores = (1 - weight) * word[0] + weight * char[0]
        order = ranking_order(scores)[:k]
        return [
            {"document": self.parts[language]["documents"][int(i)], "score": float(scores[i])}
            for i in order
            if scores[i] > 0
        ]


def response(ranked, language, mode="compact"):
    if mode not in {"compact", "expanded"}:
        raise ValueError("Choose compact or expanded previews.")
    if language not in LANGUAGES:
        raise ValueError("Unsupported language.")
    limit = 180 if mode == "compact" else 900
    results = []
    for item in ranked:
        doc = item["document"]
        results.append(
            {
                "id": doc["id"],
                "title": doc["title"],
                "preview": truncate(doc["context"], limit),
                "source": f"https://{LANGUAGES[language]}.wikipedia.org/wiki/"
                + quote(doc["title"].replace(" ", "_"), safe=""),
                "language": LANGUAGES[language],
            }
        )
    return {
        "results": results,
        "mode": mode,
        "language": language,
        "message": "" if results else "No matching source in this collection. Try another question.",
    }


def encode(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
