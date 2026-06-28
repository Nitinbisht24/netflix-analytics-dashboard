# -*- coding: utf-8 -*-
"""
core/recommender.py — Content-based "titles like this" recommender.

Builds a TF-IDF matrix over (genres + description + director) once at
startup and serves cosine-similarity nearest-neighbours from memory. This
intentionally bypasses SQLite — recommendation needs the free-text
description column and a fitted vectorizer, neither of which belong in
the aggregate tables — so it keeps its own small in-memory index built
straight from the cleaned ETL DataFrame.

This is a singleton-by-module-state design: call build() once (done at
app startup), then recommend() is cheap (~ms) for the life of the process.
"""
import threading

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core import etl

_lock = threading.Lock()
_state = {"ready": False, "df": None, "matrix": None, "title_to_idx": None}


def build() -> None:
    with _lock:
        if _state["ready"]:
            return
        df = etl.load_movie_market()
        # One row per unique title (the ETL layer explodes multi-country
        # rows, which would otherwise duplicate every title in the index)
        df = df.drop_duplicates(subset=["title"]).reset_index(drop=True)

        corpus = (
            (df["genres"].fillna("") + " ") * 3   # weight genre match higher than free text
            + df["description"].fillna("") + " "
            + df["director"].fillna("")
        )
        vectorizer = TfidfVectorizer(stop_words="english", max_features=20000, min_df=2)
        matrix = vectorizer.fit_transform(corpus)

        title_to_idx = {}
        for i, t in enumerate(df["title"].tolist()):
            title_to_idx.setdefault(t.lower(), i)

        _state.update(ready=True, df=df, matrix=matrix, title_to_idx=title_to_idx)


def is_ready() -> bool:
    return _state["ready"]


def recommend(title: str, n: int = 8) -> dict:
    if not _state["ready"]:
        build()
    df, matrix, title_to_idx = _state["df"], _state["matrix"], _state["title_to_idx"]

    idx = title_to_idx.get(title.strip().lower())
    if idx is None:
        # fall back to a "contains" match so partial/typo'd titles still work
        matches = df[df["title"].str.lower().str.contains(title.strip().lower(), regex=False, na=False)]
        if matches.empty:
            return {"query": title, "found": False, "matched_title": None, "results": []}
        idx = matches.index[0]

    sims = cosine_similarity(matrix[idx], matrix).flatten()
    order = np.argsort(-sims)
    order = [i for i in order if i != idx][:n]

    results = []
    for i in order:
        row = df.iloc[i]
        results.append({
            "title": row["title"],
            "release_year": int(row["release_year"]),
            "genres": row["genres"],
            "vote_average": round(float(row["vote_average"]), 1),
            "popularity": round(float(row["popularity"]), 1),
            "similarity": round(float(sims[i]), 3),
        })

    matched = df.iloc[idx]
    return {
        "query": title,
        "found": True,
        "matched_title": matched["title"],
        "matched_year": int(matched["release_year"]),
        "results": results,
    }


def random_seed_titles(n: int = 6) -> list:
    """A handful of well-known titles to show as example chips in the UI."""
    if not _state["ready"]:
        build()
    df = _state["df"]
    pool = df[df["popularity"] >= df["popularity"].quantile(0.97)]
    sample = pool.sample(min(n, len(pool)), random_state=None)
    return sample["title"].tolist()
