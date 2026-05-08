from keybert import KeyBERT

_model: KeyBERT | None = None


def get_keybert() -> KeyBERT:
    """Lazy-load a single KeyBERT instance. Thread-safe for read-only model inference."""
    global _model
    if _model is None:
        _model = KeyBERT(model="all-MiniLM-L6-v2")
    return _model


def extract_topics(texts: list[str], top_n: int = 5) -> list[str]:
    """
    Extract top keyword phrases from a list of review texts.

    Returns a list of capitalised keyword strings (score-filtered).
    Returns [] on empty input or any extraction failure.
    """
    if not texts:
        return []

    doc = " ".join(t.strip() for t in texts if t.strip())
    if not doc:
        return []

    try:
        kw_model = get_keybert()
        keywords = kw_model.extract_keywords(
            doc,
            keyphrase_ngram_range=(1, 2),
            stop_words="english",
            top_n=top_n,
            use_maxsum=True,
            nr_candidates=20,
        )
        return [kw.title() for kw, score in keywords if score > 0.15]
    except Exception:
        return []
