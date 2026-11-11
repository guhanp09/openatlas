import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np
import pytest

from openatlas.data import LANGUAGES, normalize, prepare
from openatlas.evaluate import choose_weight, paired_interval, ranks_for
from openatlas.search import SearchIndex, encode, ranking_order, response, select_terms, truncate, words
from openatlas.server import handler_for


@pytest.fixture
def documents():
    return [
        {
            "id": "en:1",
            "language": "english",
            "title": "Saturn",
            "context": "Saturn has bright rings of ice.",
        },
        {"id": "en:2", "language": "english", "title": "Ocean", "context": "The ocean contains salt water."},
        {"id": "bn:1", "language": "bengali", "title": "নদী", "context": "পদ্মা একটি নদী বাংলাদেশের নদী।"},
        {"id": "te:1", "language": "telugu", "title": "నది", "context": "కృష్ణా నది భారతదేశంలో ప్రవహిస్తుంది."},
    ]


@pytest.fixture
def index(documents):
    return SearchIndex(documents)


def test_unicode_word_tokens_keep_combining_marks():
    assert words("తెలుగు, বাংলা! Water") == ["తెలుగు", "বাংলা", "water"]
    assert normalize("  CAFE\u0301  ") == normalize("café")


def test_retrieval_hits_and_language_isolation(index):
    assert index.rank("Saturn rings", "english", 0.5)[0]["document"]["id"] == "en:1"
    assert index.rank("నది", "telugu", 0.5)[0]["document"]["language"] == "telugu"
    assert index.rank("নদী", "bengali", 0.5)[0]["document"]["language"] == "bengali"
    assert index.rank("Saturn rings", "telugu", 0.5) == []


def test_empty_unknown_and_invalid_query_handling(index):
    assert index.rank("  ", "english", 0.5) == []
    assert index.rank("zzzzzzzzzzzz", "english", 0.5) == []
    with pytest.raises(ValueError):
        index.rank("hello", "unsupported", 0.5)
    with pytest.raises(ValueError):
        index.rank("x" * 301, "english", 0.5)
    with pytest.raises(ValueError):
        index.rank("hello", "english", 1.1)


def test_corpus_only_vocabulary(documents):
    for row in documents:
        row["question"] = "UNSEENQUERYTOKEN"
        row["answer"] = "UNSEENANSWERTOKEN"
    model = SearchIndex(documents)
    assert "unseenquerytoken" not in model.parts["english"]["word"].vocabulary_
    assert "unseenanswertoken" not in model.parts["english"]["word"].vocabulary_


def test_stable_rank_ties_and_zero_scores():
    scores = np.array([[0.5, 0.5, 0.1], [0, 0, 0], [0.2, 0.4, 0.3]])
    assert ranks_for(scores, [1, 0, 2]).tolist() == [2, 10**9, 2]


def test_feature_cap_resolves_equal_frequency_terms_independent_of_input_order():
    terms, counts = ["z", "b", "a", "c"], [2, 3, 2, 9]
    expected = {"a": 0, "b": 1, "c": 2}
    assert select_terms(terms, counts, 3) == expected
    assert select_terms(list(reversed(terms)), list(reversed(counts)), 3) == expected


def test_numerical_rank_ties_use_document_order():
    assert ranking_order(np.array([0.5, 0.5 + 1e-15, 0.6])).tolist() == [2, 0, 1]


def test_selection_rejects_language_harm_even_with_higher_macro():
    values = {
        0: [0.5, 0.5, 0.5],
        0.25: [0.6, 0.6, 0.49],
        0.5: [0.9, 0.9, 0.4],
        0.75: [0.6, 0.6, 0.49],
        1: [0.5, 0.5, 0.5],
    }
    validation = {
        w: {lang: {"recall_at_5": score} for lang, score in zip(LANGUAGES, scores)}
        for w, scores in values.items()
    }
    assert choose_weight(validation) == 0.25


def test_paired_interval_counts_improvements_not_unpaired_difference():
    result = paired_interval([1, 7, 8, 1], [1, 2, 4, 1], draws=100)
    assert result["difference"] == 0.5
    assert 0 <= result["lower_95"] <= 0.5 <= result["upper_95"] <= 1
    assert paired_interval([1, 8], [1, 8], draws=100)["upper_95"] == 0


def test_compact_payload_preserves_sources_and_reduces_actual_bytes(documents):
    doc = dict(documents[2], context="বাংলাদেশের নদী। " * 150)
    ranked = [{"document": doc, "score": 0.6}]
    compact, expanded = [response(ranked, "bengali", mode) for mode in ["compact", "expanded"]]
    assert compact["results"][0]["id"] == expanded["results"][0]["id"]
    assert compact["results"][0]["source"] == expanded["results"][0]["source"]
    assert len(encode(compact)) < len(encode(expanded))
    assert json.loads(encode(compact))["results"][0]["title"] == "নদী"
    assert "score" not in compact["results"][0]
    with pytest.raises(ValueError):
        response(ranked, "bengali", "badmode")


def test_preview_does_not_cut_before_combining_mark():
    assert truncate("a\u0301bcdef", 1) == "a\u0301…"
    assert truncate("తెలుగు", 20) == "తెలుగు"


def test_source_url_cannot_be_injected(documents):
    doc = dict(documents[0], title='https://evil.test/<script>"')
    url = response([{"document": doc, "score": 1}], "english")["results"][0]["source"]
    assert url.startswith("https://en.wikipedia.org/wiki/")
    assert "<" not in url and '"' not in url


def test_data_split_isolation_deduplication_and_order_independence():
    def row(identifier, title, question, context):
        return {"id": "english-" + identifier, "title": title, "question": question, "context": context}

    train = [
        row("a", "Shared", "training unrelated question", "blocked article"),
        row("b", "Other", "test question", "blocked question"),
        row("c", "Safe", "safe question", "safe passage"),
        row("d", "Safe", " safe  question ", "safe passage"),
    ]
    dev = [row("e", "Shared", "test question", "evaluation passage")]
    docs, queries, counts = prepare(train, dev, validation_limit=2, background_limit=1)
    assert counts["english"]["train_rows_removed_for_overlap"] == 2
    assert len(queries["validation"]) == 1
    assert len(queries["evaluation"]) == 1
    assert {d["context"] for d in docs} == {"safe passage", "evaluation passage"}
    assert {q["gold"] for rows in queries.values() for q in rows} <= {d["id"] for d in docs}
    assert prepare(list(reversed(train)), dev, 2, 1) == (docs, queries, counts)


def test_http_contract_and_path_boundary(index):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(index, 0.5))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/api/search?q=rings&language=english") as result:
            assert json.load(result)["results"][0]["title"] == "Saturn"
            assert result.headers["Cache-Control"] == "no-store"
            assert "object-src 'none'" in result.headers["Content-Security-Policy"]
        for path, status in [("/../../pyproject.toml", 404), ("/api/search?q=x&language=unknown", 400)]:
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + path)
            assert error.value.code == status
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
