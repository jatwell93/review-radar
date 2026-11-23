from services.sentiment import classify, score_review


def test_classify_thresholds():
    assert classify(0.05) == "positive"
    assert classify(-0.05) == "negative"
    assert classify(0.0) == "neutral"


def test_score_review_is_signed_and_bounded():
    good = score_review("Great food and friendly staff, loved it")
    bad = score_review("Terrible service, cold food, never again")
    assert 0 < good <= 1
    assert -1 <= bad < 0
