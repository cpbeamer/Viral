"""
Viral Feed Algorithm

Simulates a social media feed ranking algorithm with configurable weights.
Determines which posts each agent sees in their feed based on:
- Recency: newer posts rank higher
- Popularity: more engaged posts rank higher
- Relevance: topic overlap with agent's interests
- Echo Chamber: posts from similar vibe_profiles rank higher

This drives the cascade mechanics: agents can only engage with posts
they "see" in their feed, and the feed algorithm controls visibility.
"""

import random
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from ..utils.logger import get_logger

logger = get_logger('viral.feed_algorithm')


@dataclass
class FeedPost:
    """A post as it appears in an agent's feed."""
    post_id: str
    author_id: int
    content: str
    created_round: int
    # Engagement metrics
    like_count: int = 0
    repost_count: int = 0
    quote_count: int = 0
    reply_count: int = 0
    # Author attributes
    author_reach: float = 0.0
    author_vibe: str = "Neutral"
    author_topics: List[str] = None
    # Feed ranking score (computed by the algorithm)
    feed_score: float = 0.0
    # Cascade depth — how many hops from original
    cascade_depth: int = 0
    # The agent who surfaced this post (via repost/quote)
    surfaced_by: Optional[int] = None

    def __post_init__(self):
        if self.author_topics is None:
            self.author_topics = []


@dataclass
class FeedConfig:
    """Configuration for the feed ranking algorithm."""
    # Weight factors (should sum to ~1.0 for normalization)
    recency_weight: float = 0.30
    popularity_weight: float = 0.30
    relevance_weight: float = 0.20
    echo_chamber_weight: float = 0.20

    # How many posts each agent sees per round
    feed_size: int = 15

    # Decay rate for recency (per round)
    recency_decay: float = 0.15

    # Minimum score to appear in feed (filters out noise)
    min_score_threshold: float = 0.01

    # Randomization factor (adds noise to prevent deterministic feeds)
    noise_factor: float = 0.10


def compute_feed(
    agent_id: int,
    agent_topics: List[str],
    agent_vibe: str,
    agent_susceptibility: float,
    current_round: int,
    available_posts: List[FeedPost],
    following: List[int],
    config: FeedConfig,
) -> List[FeedPost]:
    """
    Compute the ranked feed for a single agent.

    Args:
        agent_id: The agent consuming the feed
        agent_topics: Agent's interested topics
        agent_vibe: Agent's vibe profile
        agent_susceptibility: Agent's susceptibility score
        current_round: Current simulation round
        available_posts: All posts available for the feed
        following: List of agent IDs this agent follows
        config: Feed configuration

    Returns:
        Ranked list of FeedPost objects the agent will see
    """
    if not available_posts:
        return []

    scored_posts: List[Tuple[float, FeedPost]] = []

    for post in available_posts:
        # Skip agent's own posts
        if post.author_id == agent_id:
            continue

        # --- 1. Recency Score ---
        age_rounds = max(0, current_round - post.created_round)
        recency_score = max(0.0, 1.0 - age_rounds * config.recency_decay)

        # --- 2. Popularity Score ---
        total_engagement = (
            post.like_count + post.repost_count * 2 +
            post.quote_count * 3 + post.reply_count * 1.5
        )
        # Log scale to prevent mega-viral posts from completely dominating
        popularity_score = min(1.0, _log_normalize(total_engagement, scale=50.0))

        # --- 3. Relevance Score ---
        relevance_score = _topic_overlap(agent_topics, post.author_topics)

        # Following bonus: posts from followed accounts get a relevance boost
        if post.author_id in following or (post.surfaced_by and post.surfaced_by in following):
            relevance_score = min(1.0, relevance_score + 0.3)

        # --- 4. Echo Chamber Score ---
        echo_score = _vibe_similarity(agent_vibe, post.author_vibe)

        # --- Weighted combination ---
        score = (
            config.recency_weight * recency_score +
            config.popularity_weight * popularity_score +
            config.relevance_weight * relevance_score +
            config.echo_chamber_weight * echo_score
        )

        # Author reach bonus (high-reach authors get visibility boost)
        score *= (1.0 + post.author_reach * 0.5)

        # Add noise to prevent deterministic feeds
        noise = random.gauss(0, config.noise_factor)
        score = max(0.0, score + noise)

        if score >= config.min_score_threshold:
            post.feed_score = score
            scored_posts.append((score, post))

    # Sort by score descending, take top feed_size
    scored_posts.sort(key=lambda x: x[0], reverse=True)
    return [post for _, post in scored_posts[:config.feed_size]]


def should_agent_engage(
    agent_susceptibility: float,
    agent_vibe: str,
    post: FeedPost,
    base_engagement_rate: float = 0.15,
) -> Tuple[bool, Optional[str]]:
    """
    Determine if an agent engages with a post, and what type of engagement.

    Uses susceptibility_score and vibe_profile to drive behavior.

    Args:
        agent_susceptibility: Agent's susceptibility score (0.0-1.0)
        agent_vibe: Agent's vibe profile
        post: The post being evaluated
        base_engagement_rate: Base probability of any engagement

    Returns:
        Tuple of (should_engage, engagement_type)
        engagement_type is one of: "like", "repost", "quote", "reply", None
    """
    # Base probability modified by susceptibility
    engagement_prob = base_engagement_rate * (0.5 + agent_susceptibility)

    # Vibe-specific behavior modifiers
    vibe_modifiers = _get_vibe_engagement_modifiers(agent_vibe)

    # Popular posts have higher engagement probability
    popularity_boost = min(0.3, post.like_count * 0.005 + post.repost_count * 0.01)
    engagement_prob += popularity_boost

    # Clamp probability
    engagement_prob = min(0.95, max(0.01, engagement_prob))

    if random.random() > engagement_prob:
        return False, None

    # Determine engagement type based on vibe profile
    action_weights = {
        "like": vibe_modifiers.get("like_weight", 0.50),
        "repost": vibe_modifiers.get("repost_weight", 0.25),
        "quote": vibe_modifiers.get("quote_weight", 0.15),
        "reply": vibe_modifiers.get("reply_weight", 0.10),
    }

    actions = list(action_weights.keys())
    weights = list(action_weights.values())
    chosen = random.choices(actions, weights=weights, k=1)[0]

    return True, chosen


def _get_vibe_engagement_modifiers(vibe: str) -> Dict[str, float]:
    """Get engagement type weights based on agent's vibe profile."""
    modifiers = {
        "Skeptical": {
            "like_weight": 0.20, "repost_weight": 0.05,
            "quote_weight": 0.35, "reply_weight": 0.40,
        },
        "Aggressive": {
            "like_weight": 0.15, "repost_weight": 0.20,
            "quote_weight": 0.40, "reply_weight": 0.25,
        },
        "Helpful": {
            "like_weight": 0.30, "repost_weight": 0.15,
            "quote_weight": 0.20, "reply_weight": 0.35,
        },
        "Opportunistic": {
            "like_weight": 0.25, "repost_weight": 0.35,
            "quote_weight": 0.25, "reply_weight": 0.15,
        },
        "Neutral": {
            "like_weight": 0.55, "repost_weight": 0.20,
            "quote_weight": 0.10, "reply_weight": 0.15,
        },
        "Contrarian": {
            "like_weight": 0.10, "repost_weight": 0.10,
            "quote_weight": 0.45, "reply_weight": 0.35,
        },
        "Amplifier": {
            "like_weight": 0.25, "repost_weight": 0.50,
            "quote_weight": 0.15, "reply_weight": 0.10,
        },
    }
    return modifiers.get(vibe, modifiers["Neutral"])


def _topic_overlap(agent_topics: List[str], post_topics: List[str]) -> float:
    """Calculate topic overlap as a 0-1 score."""
    if not agent_topics or not post_topics:
        return 0.1  # Small base relevance

    agent_set = set(t.lower() for t in agent_topics)
    post_set = set(t.lower() for t in post_topics)

    overlap = len(agent_set & post_set)
    total = len(agent_set | post_set)

    return overlap / total if total > 0 else 0.0


def _vibe_similarity(vibe_a: str, vibe_b: str) -> float:
    """
    Calculate similarity between two vibe profiles.

    Same vibes have high similarity; opposing vibes have low similarity.
    This drives the echo chamber effect.
    """
    if vibe_a == vibe_b:
        return 1.0

    # Affinity matrix: vibes that tend to amplify each other
    affinities = {
        ("Amplifier", "Opportunistic"): 0.8,
        ("Amplifier", "Aggressive"): 0.7,
        ("Aggressive", "Contrarian"): 0.6,
        ("Helpful", "Skeptical"): 0.7,
        ("Neutral", "Helpful"): 0.6,
        ("Opportunistic", "Amplifier"): 0.8,
        ("Aggressive", "Amplifier"): 0.7,
        ("Contrarian", "Aggressive"): 0.6,
        ("Skeptical", "Helpful"): 0.7,
        ("Helpful", "Neutral"): 0.6,
    }

    pair = (vibe_a, vibe_b)
    if pair in affinities:
        return affinities[pair]

    # Default: moderate similarity
    return 0.3


def _log_normalize(value: float, scale: float = 50.0) -> float:
    """Logarithmic normalization to prevent extreme values from dominating."""
    import math
    if value <= 0:
        return 0.0
    return math.log(1.0 + value) / math.log(1.0 + scale)
