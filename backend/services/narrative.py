import os
from anthropic import Anthropic


def generate_narrative(data: dict) -> str:
    """Call Claude Haiku to produce a plain-English pharmacy advisor summary."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    top_texts = "\n".join(
        f"- {r['text'][:200]}" for r in data.get("top_reviews", [])[:3]
    )
    bottom_texts = "\n".join(
        f"- {r['text'][:200]}" for r in data.get("bottom_reviews", [])[:3]
    )

    previous_score = data.get("previous_score")
    previous_distribution = data.get("previous_distribution")

    if previous_score is not None:
        delta = data["overall_score"] - previous_score
        if delta > 0.02:
            direction = "improved"
        elif delta < -0.02:
            direction = "declined"
        else:
            direction = "held steady"
        trend_block = (
            f"\nTrend vs previous analysis: overall score {direction} "
            f"({previous_score:.2f} → {data['overall_score']:.2f})"
        )
        if previous_distribution:
            pos_delta = data["distribution"]["positive"] - previous_distribution.get("positive", 0)
            neg_delta = data["distribution"]["negative"] - previous_distribution.get("negative", 0)
            trend_block += (
                f"\nPositive reviews: {'+' if pos_delta >= 0 else ''}{pos_delta}, "
                f"Negative reviews: {'+' if neg_delta >= 0 else ''}{neg_delta}"
            )
        trend_section = trend_block + "\n"
        trend_instruction = "5. Whether performance has improved, declined, or held steady vs the previous analysis.\n"
    else:
        trend_section = ""
        trend_instruction = ""

    prompt = f"""You are a business advisor helping a pharmacy owner understand their Google review sentiment data.

Analysis summary:
- Total reviews: {data['total_reviews']}
- Overall sentiment score: {data['overall_score']:.2f} (scale: -1 very negative to +1 very positive)
- Positive reviews: {data['distribution']['positive']}
- Neutral reviews: {data['distribution']['neutral']}
- Negative reviews: {data['distribution']['negative']}
{trend_section}
Most positive reviews:
{top_texts if top_texts else "None available"}

Most critical reviews:
{bottom_texts if bottom_texts else "None available"}

Write a 3-4 sentence plain-English summary for the pharmacy owner. Cover:
1. Overall performance (is this good, average, or needs work?)
2. What customers consistently appreciate
3. The primary area to improve
4. One specific, actionable recommendation
{trend_instruction}
Use a warm, professional business-advisor tone. No jargon. No bullet points. Sentences only."""

    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()
