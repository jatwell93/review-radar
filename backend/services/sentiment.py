from collections import defaultdict

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Instantiate once at module level — loading the lexicon is slow; do NOT create per-request
_analyzer = SentimentIntensityAnalyzer()


def score_review(text: str) -> float:
    """Return VADER compound score in range [-1.0, 1.0]."""
    return _analyzer.polarity_scores(text)["compound"]


def classify(compound: float) -> str:
    """Classify a compound score as positive, neutral, or negative."""
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def run_sentiment_pipeline(reviews: list[dict]) -> dict:
    # Defensive guard — CSV parser already raises ValueError for empty input,
    # but guard here in case caller bypasses the parser.
    if not reviews:
        return {
            "total_reviews": 0,
            "overall_score": 0.0,
            "distribution": {"positive": 0, "neutral": 0, "negative": 0},
            "timeline": [],
            "top_reviews": [],
            "bottom_reviews": [],
        }

    # Score each review
    for r in reviews:
        r["compound"] = score_review(r["text"])

    # overall_score: mean of compound values
    overall_score = round(sum(r["compound"] for r in reviews) / len(reviews), 4)

    # distribution
    distribution = {"positive": 0, "neutral": 0, "negative": 0}
    for r in reviews:
        distribution[classify(r["compound"])] += 1

    # timeline: group by YYYY-MM for reviews that have parseable dates
    try:
        from dateutil import parser as dateutil_parser

        month_groups: dict[str, list[float]] = defaultdict(list)
        for r in reviews:
            raw_date = r.get("date")
            if not raw_date:
                continue
            try:
                parsed = dateutil_parser.parse(raw_date, dayfirst=False)
                month_key = parsed.strftime("%Y-%m")
                month_groups[month_key].append(r["compound"])
            except (ValueError, OverflowError):
                continue

        timeline = [
            {
                "month": month,
                "avg_score": round(sum(scores) / len(scores), 4),
                "count": len(scores),
            }
            for month, scores in sorted(month_groups.items())
        ]
    except ImportError:
        timeline = []

    # top_reviews: up to 5 highest compound scores
    # bottom_reviews: up to 5 lowest compound scores
    # Note: when total_reviews < 10, the same review may appear in both lists.
    # This is intentional — the frontend (01-03) should handle this case gracefully.
    sorted_desc = sorted(reviews, key=lambda r: r["compound"], reverse=True)
    sorted_asc = sorted(reviews, key=lambda r: r["compound"])

    top_reviews = [{"text": r["text"], "score": r["compound"]} for r in sorted_desc[:5]]
    bottom_reviews = [{"text": r["text"], "score": r["compound"]} for r in sorted_asc[:5]]

    return {
        "total_reviews": len(reviews),
        "overall_score": overall_score,
        "distribution": distribution,
        "timeline": timeline,
        "top_reviews": top_reviews,
        "bottom_reviews": bottom_reviews,
    }
