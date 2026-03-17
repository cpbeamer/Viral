"""
Viral Sentiment Analyzer

Lightweight sentiment analysis for simulation posts and engagements.
Uses a simple lexicon-based approach as the default (no external API calls),
with an optional LLM-based mode for higher accuracy.

The lexicon approach provides fast, cost-free sentiment scoring suitable
for processing thousands of posts per round without API costs.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger('viral.sentiment_analyzer')


# Positive sentiment keywords with weights
_POSITIVE_LEXICON: Dict[str, float] = {
    # English
    "good": 0.5, "great": 0.7, "amazing": 0.8, "awesome": 0.8,
    "excellent": 0.9, "love": 0.7, "wonderful": 0.8, "fantastic": 0.8,
    "best": 0.7, "beautiful": 0.6, "happy": 0.6, "perfect": 0.8,
    "brilliant": 0.7, "outstanding": 0.8, "incredible": 0.8,
    "support": 0.5, "agree": 0.5, "thanks": 0.4, "helpful": 0.6,
    "progress": 0.5, "win": 0.6, "success": 0.7, "hope": 0.5,
    "excited": 0.6, "proud": 0.6, "impressive": 0.7,
    "bullish": 0.6, "moon": 0.5, "based": 0.4,
    # Chinese
    "好": 0.5, "棒": 0.6, "优秀": 0.7, "厉害": 0.6, "牛": 0.5,
    "支持": 0.5, "赞": 0.6, "喜欢": 0.5, "感谢": 0.4, "完美": 0.8,
    "了不起": 0.7, "开心": 0.6, "希望": 0.5, "进步": 0.5,
}

# Negative sentiment keywords with weights
_NEGATIVE_LEXICON: Dict[str, float] = {
    # English
    "bad": -0.5, "terrible": -0.8, "awful": -0.8, "horrible": -0.8,
    "hate": -0.7, "disgusting": -0.9, "worst": -0.8, "stupid": -0.6,
    "angry": -0.6, "outrage": -0.7, "scandal": -0.6, "fake": -0.5,
    "scam": -0.7, "fraud": -0.8, "corrupt": -0.7, "lie": -0.6,
    "lies": -0.6, "fail": -0.5, "failure": -0.6, "disaster": -0.7,
    "pathetic": -0.7, "toxic": -0.6, "shame": -0.6, "unacceptable": -0.7,
    "bearish": -0.6, "rug": -0.7, "dump": -0.5, "crash": -0.6,
    # Chinese
    "坏": -0.5, "差": -0.5, "垃圾": -0.7, "愤怒": -0.6, "失望": -0.6,
    "骗": -0.7, "造假": -0.7, "恶心": -0.8, "可耻": -0.7, "无耻": -0.8,
    "讨厌": -0.6, "反对": -0.5, "丑闻": -0.6, "腐败": -0.7,
}

# Intensifiers that amplify sentiment
_INTENSIFIERS: Dict[str, float] = {
    "very": 1.3, "extremely": 1.5, "absolutely": 1.5, "incredibly": 1.4,
    "totally": 1.3, "completely": 1.3, "utterly": 1.4, "really": 1.2,
    "so": 1.2, "super": 1.3, "highly": 1.3,
    "非常": 1.3, "极其": 1.5, "太": 1.3, "真的": 1.2,
}

# Negation words that flip sentiment
_NEGATIONS = {
    "not", "no", "never", "neither", "nor", "none", "don't", "doesn't",
    "didn't", "won't", "wouldn't", "couldn't", "shouldn't", "isn't",
    "aren't", "wasn't", "weren't", "can't", "cannot",
    "不", "没", "没有", "别", "莫", "未",
}


def analyze_sentiment(text: str) -> float:
    """
    Analyze the sentiment of a text using lexicon-based scoring.

    Args:
        text: The text to analyze

    Returns:
        Sentiment score from -1.0 (very negative) to 1.0 (very positive)
    """
    if not text:
        return 0.0

    # Tokenize — for CJK (Chinese/Japanese/Korean) characters,
    # split into individual characters since our lexicon uses single chars
    raw_tokens = re.findall(r'[\w]+', text.lower())
    words: list = []
    for token in raw_tokens:
        # Check if any character is CJK
        has_cjk = any('\u4e00' <= c <= '\u9fff' for c in token)
        if has_cjk:
            # Split CJK token into individual characters
            for c in token:
                if '\u4e00' <= c <= '\u9fff':
                    words.append(c)
                elif c.isalnum():
                    words.append(c)
        else:
            words.append(token)

    total_score = 0.0
    word_count = 0
    negation_active = False
    intensifier = 1.0

    for i, word in enumerate(words):
        # Check for negation
        if word in _NEGATIONS:
            negation_active = True
            continue

        # Check for intensifier
        if word in _INTENSIFIERS:
            intensifier = _INTENSIFIERS[word]
            continue

        # Check positive lexicon
        if word in _POSITIVE_LEXICON:
            score = _POSITIVE_LEXICON[word] * intensifier
            if negation_active:
                score = -score * 0.8  # Negation flips and slightly dampens
            total_score += score
            word_count += 1
            negation_active = False
            intensifier = 1.0
            continue

        # Check negative lexicon
        if word in _NEGATIVE_LEXICON:
            score = _NEGATIVE_LEXICON[word] * intensifier
            if negation_active:
                score = -score * 0.8
            total_score += score
            word_count += 1
            negation_active = False
            intensifier = 1.0
            continue

        # Reset modifiers after a non-sentiment word
        if word_count > 0 or i > 3:
            negation_active = False
            intensifier = 1.0

    if word_count == 0:
        return 0.0

    # Normalize: average score, clamped to [-1, 1]
    avg_score = total_score / word_count
    return max(-1.0, min(1.0, avg_score))


def batch_analyze_sentiment(texts: List[str]) -> List[float]:
    """Analyze sentiment for a batch of texts."""
    return [analyze_sentiment(text) for text in texts]


def get_round_sentiment_summary(
    sentiments: List[float],
) -> Dict[str, Any]:
    """
    Summarize sentiment distribution for a single round.

    Args:
        sentiments: List of sentiment scores from the round

    Returns:
        Summary with positive/negative/neutral counts and averages
    """
    if not sentiments:
        return {
            "avg_sentiment": 0.0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "total": 0,
        }

    positive = sum(1 for s in sentiments if s > 0.1)
    negative = sum(1 for s in sentiments if s < -0.1)
    neutral = len(sentiments) - positive - negative

    return {
        "avg_sentiment": round(sum(sentiments) / len(sentiments), 3),
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": neutral,
        "total": len(sentiments),
        "positive_ratio": round(positive / len(sentiments), 3),
        "negative_ratio": round(negative / len(sentiments), 3),
    }


def build_llm_sentiment_prompt(texts: List[str]) -> str:
    """
    Build a batch LLM prompt for sentiment analysis (for high-accuracy mode).

    Args:
        texts: Up to 20 texts to analyze in one call

    Returns:
        Formatted prompt string
    """
    numbered = "\n".join(f"{i+1}. {t[:200]}" for i, t in enumerate(texts[:20]))
    return f"""Analyze the sentiment of each text below. Return a JSON array of numbers,
where each number is the sentiment score from -1.0 (very negative) to 1.0 (very positive).

Texts:
{numbered}

Return ONLY a JSON array like: [-0.5, 0.3, 0.0, ...]"""
