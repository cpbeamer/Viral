"""
Viral Mutation Engine

When a high-influence agent "quote tweets" a post, the mutation engine
uses the LLM to rewrite the content through the lens of the agent's
vibe_profile. This simulates how narratives mutate as they cascade
through a social network.

For cost efficiency, only the top ~1% of agents (by reach_score) get
full LLM-powered mutations. Lower-tier agents use template-based
mutations with simple word substitution.

Tracks "mutation distance" from the seed post to measure narrative drift.
"""

import random
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher

from ..utils.logger import get_logger

logger = get_logger('viral.mutation_engine')


# Template-based mutations for low-tier agents (no LLM call)
_MUTATION_TEMPLATES: Dict[str, List[str]] = {
    "Skeptical": [
        "Wait, is this actually real? \"{content}\" — I'd love to see a source for this.",
        "Not sure I buy this: \"{content}\" Feels like there's more to the story.",
        "Before everyone jumps on this — \"{content}\" — has anyone verified this?",
        "🤔 \"{content}\" — I have some serious doubts about this take.",
    ],
    "Aggressive": [
        "LMAO this is exactly the problem: \"{content}\" — wake up people!!!",
        "Can't believe anyone actually thinks \"{content}\" is okay. Absolutely unhinged.",
        "This right here 👇 \"{content}\" — and nobody's doing ANYTHING about it!",
        "They really said \"{content}\" and thought we wouldn't notice. Disgraceful.",
    ],
    "Helpful": [
        "For context on \"{content}\" — here's what I know about the background...",
        "Adding some nuance to \"{content}\" — it's worth noting that...",
        "Seen a lot of confusion on this. \"{content}\" — let me break down the key points.",
        "📌 Important thread on \"{content}\" — sharing for awareness.",
    ],
    "Opportunistic": [
        "🚨 BREAKING: \"{content}\" — this changes EVERYTHING. Thread 🧵👇",
        "Everyone's talking about \"{content}\" but nobody's seeing the real opportunity here...",
        "HOT TAKE: \"{content}\" — and here's why this is actually bullish 📈",
        "If you're sleeping on \"{content}\" you're ngmi. Here's the alpha 🧵",
    ],
    "Neutral": [
        "Interesting: \"{content}\"",
        "Saw this — \"{content}\" — thoughts?",
        "\"{content}\" — hm, not sure what to think about this one.",
    ],
    "Contrarian": [
        "Everyone's saying \"{content}\" but here's why they're wrong...",
        "Unpopular opinion: the opposite of \"{content}\" is actually true.",
        "Y'all are all falling for \"{content}\" — classic groupthink.",
        "Devil's advocate on \"{content}\" — what if it's the exact opposite?",
    ],
    "Amplifier": [
        "RT!! \"{content}\" — everyone needs to see this!! 🔥🔥",
        "📢 SIGNAL BOOST: \"{content}\"",
        "This!! 👆 \"{content}\" — retweet to spread awareness!",
        "🚨🚨 \"{content}\" — share this far and wide!",
    ],
}

# Sentiment shift per vibe (how much the vibe changes the sentiment)
_VIBE_SENTIMENT_SHIFT: Dict[str, float] = {
    "Skeptical": -0.15,
    "Aggressive": -0.30,
    "Helpful": 0.10,
    "Opportunistic": 0.05,
    "Neutral": 0.00,
    "Contrarian": -0.10,
    "Amplifier": 0.05,
}

# LLM prompts for high-tier mutation
_LLM_MUTATION_PROMPT = """You are @{username}, a social media user with the following profile:
- Vibe: {vibe_profile}
- Bio: {bio}
- Personality: {persona_snippet}

You just saw this post and want to quote-tweet it in your own voice:
Original post: "{content}"

Write a quote-tweet (1-3 sentences max) that:
1. Reframes the content through YOUR perspective and vibe
2. Sounds natural and authentic to your character
3. Adds your own spin or commentary

Only output the quote-tweet text, nothing else."""


def mutate_content_template(
    original_content: str,
    vibe_profile: str,
) -> Dict[str, Any]:
    """
    Generate a template-based mutation (no LLM call).
    Used for the bottom 90% of agents to keep costs low.

    Args:
        original_content: The original post content
        vibe_profile: The quoting agent's vibe profile

    Returns:
        Dict with 'mutated_content', 'mutation_distance', 'sentiment_shift'
    """
    templates = _MUTATION_TEMPLATES.get(vibe_profile, _MUTATION_TEMPLATES["Neutral"])
    template = random.choice(templates)

    # Truncate long content for the template
    short_content = original_content[:120]
    if len(original_content) > 120:
        short_content += "..."

    mutated = template.format(content=short_content)

    # Calculate mutation distance (0.0 = identical, 1.0 = completely different)
    distance = 1.0 - SequenceMatcher(None, original_content, mutated).ratio()

    # Sentiment shift
    sentiment_shift = _VIBE_SENTIMENT_SHIFT.get(vibe_profile, 0.0)
    # Add some noise
    sentiment_shift += random.gauss(0, 0.1)

    return {
        "mutated_content": mutated,
        "mutation_distance": round(distance, 3),
        "sentiment_shift": round(max(-1.0, min(1.0, sentiment_shift)), 3),
        "method": "template",
    }


def build_llm_mutation_prompt(
    original_content: str,
    username: str,
    vibe_profile: str,
    bio: str,
    persona: str,
) -> str:
    """
    Build the LLM prompt for high-tier agent mutations.
    Used for the top ~1% of agents.

    Args:
        original_content: The post being quote-tweeted
        username: The quoting agent's username
        vibe_profile: Vibe profile string
        bio: Agent's bio
        persona: Agent's full persona (will be truncated)

    Returns:
        Formatted prompt string ready for the LLM
    """
    # Truncate persona to keep prompt short
    persona_snippet = persona[:300] + "..." if len(persona) > 300 else persona

    return _LLM_MUTATION_PROMPT.format(
        username=username,
        vibe_profile=vibe_profile,
        bio=bio,
        persona_snippet=persona_snippet,
        content=original_content[:500],
    )


def parse_llm_mutation(
    original_content: str,
    llm_response: str,
    vibe_profile: str,
) -> Dict[str, Any]:
    """
    Parse the LLM response into a mutation result.

    Args:
        original_content: The original post
        llm_response: The LLM's generated quote-tweet
        vibe_profile: The quoting agent's vibe

    Returns:
        Dict with 'mutated_content', 'mutation_distance', 'sentiment_shift'
    """
    # Clean up LLM response
    mutated = llm_response.strip().strip('"').strip("'")

    # Calculate mutation distance
    distance = 1.0 - SequenceMatcher(None, original_content, mutated).ratio()

    # Estimate sentiment shift from vibe
    sentiment_shift = _VIBE_SENTIMENT_SHIFT.get(vibe_profile, 0.0)

    return {
        "mutated_content": mutated,
        "mutation_distance": round(distance, 3),
        "sentiment_shift": round(max(-1.0, min(1.0, sentiment_shift)), 3),
        "method": "llm",
    }


def get_mutation_genome(mutations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the "Information Virus Genome" — how a seed message has
    mutated through the network.

    Args:
        mutations: List of mutation dicts from PostCascade.mutations

    Returns:
        Genome analysis with average drift, dominant vibes, etc.
    """
    if not mutations:
        return {
            "total_mutations": 0,
            "avg_distance": 0.0,
            "max_depth": 0,
            "sentiment_trajectory": [],
        }

    avg_distance = sum(m.get("mutation_distance", 0) for m in mutations) / len(mutations)
    max_depth = max(m.get("depth", 0) for m in mutations)

    # Track sentiment trajectory by depth
    sentiment_by_depth: Dict[int, List[float]] = {}
    for m in mutations:
        d = m.get("depth", 0)
        s = m.get("sentiment_shift", 0.0)
        if d not in sentiment_by_depth:
            sentiment_by_depth[d] = []
        sentiment_by_depth[d].append(s)

    trajectory = []
    for depth in sorted(sentiment_by_depth.keys()):
        values = sentiment_by_depth[depth]
        trajectory.append({
            "depth": depth,
            "avg_sentiment_shift": round(sum(values) / len(values), 3),
            "mutation_count": len(values),
        })

    return {
        "total_mutations": len(mutations),
        "avg_distance": round(avg_distance, 3),
        "max_depth": max_depth,
        "sentiment_trajectory": trajectory,
    }
