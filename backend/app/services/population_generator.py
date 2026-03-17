"""
Viral Population Generator
Batch-generates large agent populations (up to 10,000+) for cascade simulation
without requiring individual LLM calls for every agent.

Strategy:
1. Load archetype distribution from a subculture config
2. Assign archetypes using weighted random sampling
3. Generate demographics (age, gender, profession, topics) from the config
4. Generate a social graph using Barabási–Albert power-law model
5. Optionally enrich high-influence agents with LLM-generated bios

The key insight: only the top ~1% of agents (by reach_score) get LLM-enriched
personas. The remaining 99% use template-based profile generation, keeping
inference costs manageable at scale.
"""

import json
import math
import os
import random
from typing import Dict, Any, List, Optional, Tuple

from ..utils.logger import get_logger
from .oasis_profile_generator import OasisAgentProfile, VIBE_PROFILES

logger = get_logger('viral.population_generator')

# Path to subculture config data
_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
_SUBCULTURES_PATH = os.path.join(_DATA_DIR, 'subcultures.json')


def _load_subcultures() -> Dict[str, Any]:
    """Load subculture definitions from the JSON config."""
    try:
        with open(_SUBCULTURES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Subcultures config not found at {_SUBCULTURES_PATH}, using empty config")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse subcultures config: {e}")
        return {}


def _power_law_sample(n: int, exponent: float = 2.5, x_min: float = 0.01) -> List[float]:
    """
    Generate n samples from a power-law distribution, normalized to [0, 1].

    Uses inverse transform sampling:
        x = x_min * (1 - u)^(-1/(alpha-1))
    where u ~ Uniform(0,1) and alpha is the exponent.

    Higher exponent → more concentrated at the low end (most agents have low
    reach, a tiny fraction have very high reach).
    """
    if exponent <= 1.0:
        exponent = 2.0  # Safety fallback

    samples: List[float] = []
    inv_alpha = 1.0 / (exponent - 1.0)

    for _ in range(n):
        u = random.random()
        # Avoid division by zero
        u = max(u, 1e-10)
        raw = x_min * (1.0 - u) ** (-inv_alpha)
        samples.append(raw)

    # Normalize to [0, 1]
    max_val = max(samples) if samples else 1.0
    if max_val > 0:
        samples = [s / max_val for s in samples]

    return samples


def _follower_count_from_reach(
    reach_score: float,
    min_followers: int,
    max_followers: int
) -> int:
    """Convert a 0-1 reach_score to a follower count using exponential scaling."""
    # Exponential mapping: small reach → few followers, high reach → many
    log_min = math.log(max(min_followers, 1))
    log_max = math.log(max(max_followers, 2))
    log_count = log_min + reach_score * (log_max - log_min)
    return int(math.exp(log_count))


def _generate_username(name: str, idx: int) -> str:
    """Generate a plausible username from a name and index."""
    base = name.lower().replace(" ", "_").replace(".", "")
    base = ''.join(c for c in base if c.isalnum() or c == '_')
    suffix = random.randint(10, 999)
    return f"{base}_{suffix}"


# --- Persona template strings per vibe archetype ---

_PERSONA_TEMPLATES: Dict[str, str] = {
    "Skeptical": (
        "{name} is a {age}-year-old {profession} from {country}. "
        "They are naturally skeptical of viral claims and trending narratives. "
        "Before sharing anything, they verify sources and cross-reference facts. "
        "They often post threads debunking misinformation and challenge popular opinions "
        "with evidence-based arguments. "
        "On social media, they follow credible news outlets and researchers. "
        "They tend to have moderate engagement — they don't post frequently but their "
        "contributions carry weight. "
        "Topics of interest: {topics}."
    ),
    "Aggressive": (
        "{name} is a {age}-year-old {profession} from {country}. "
        "They are a confrontational voice on social media, quick to attack perceived "
        "opponents and amplify outrage. They use strong, emotionally charged language "
        "and rarely back down from arguments. "
        "Their feed is a mix of hot takes, pointed quote-tweets, and aggressive retorts. "
        "They thrive in controversy and often pile on to trending drama. "
        "Despite their combative style, they have carved out a loyal following who share "
        "their worldview. "
        "Topics of interest: {topics}."
    ),
    "Helpful": (
        "{name} is a {age}-year-old {profession} from {country}. "
        "They approach social media as a way to inform and educate. "
        "They share useful context, explanations, and resources. "
        "When misinformation spreads, they calmly provide corrections with links to "
        "reliable sources. "
        "They engage constructively in discussions and are known for their balanced, "
        "measured tone. They attract followers who value substance over drama. "
        "Topics of interest: {topics}."
    ),
    "Opportunistic": (
        "{name} is a {age}-year-old {profession} from {country}. "
        "They are a trend-surfer who jumps on any viral topic for maximum engagement. "
        "Their posting strategy is calculated — they time their takes to ride the wave "
        "of trending hashtags. "
        "They don't deeply believe in every take they post; it's about eyeballs, growth, "
        "and staying relevant. They're expert at crafting engagement-bait. "
        "Their follower count is high relative to their genuine influence. "
        "Topics of interest: {topics}."
    ),
    "Neutral": (
        "{name} is a {age}-year-old {profession} from {country}. "
        "They are a casual social media user who scrolls their feed, occasionally likes "
        "posts, and rarely creates original content. "
        "They don't have strong opinions on most trending topics and tend to observe "
        "rather than participate in heated discussions. "
        "They follow a mix of entertainment, news, and personal connections. "
        "Their engagement is sporadic and low-pressure. "
        "Topics of interest: {topics}."
    ),
    "Contrarian": (
        "{name} is a {age}-year-old {profession} from {country}. "
        "They instinctively push back against whatever the majority believes. "
        "If a take is trending, they'll find the opposing angle. "
        "They pride themselves on 'independent thinking' and often devils-advocate "
        "their way through discussions. "
        "Their posts generate high engagement because they trigger both supporters "
        "and detractors. They are polarizing figures in any conversation. "
        "Topics of interest: {topics}."
    ),
    "Amplifier": (
        "{name} is a {age}-year-old {profession} from {country}. "
        "They are a maximum-engagement retweet machine. "
        "They rarely create original content but obsessively repost, quote-tweet, "
        "and signal-boost anything that catches their eye. "
        "They have high susceptibility to viral content and act as superspreader "
        "nodes in information cascades. "
        "Their feed is a firehose of reshared content with minimal commentary. "
        "Topics of interest: {topics}."
    ),
}


def generate_population(
    subculture: str = "default",
    count: int = 10000,
    seed: Optional[int] = None,
) -> List[OasisAgentProfile]:
    """
    Generate a batch of agent profiles for a given subculture.

    Args:
        subculture: Key from subcultures.json (e.g., "crypto_twitter")
        count: Number of agents to generate (default 10,000)
        seed: Optional random seed for reproducibility

    Returns:
        List of OasisAgentProfile instances
    """
    if seed is not None:
        random.seed(seed)

    # Load subculture config
    subcultures = _load_subcultures()
    config = subcultures.get(subculture)
    if not config:
        logger.warning(f"Subculture '{subculture}' not found, falling back to 'default'")
        config = subcultures.get("default", {})

    if not config:
        raise ValueError(
            f"No subculture config available. Ensure {_SUBCULTURES_PATH} exists."
        )

    logger.info(f"Generating {count} agents for subculture '{config.get('name', subculture)}'")

    # --- 1. Assign archetypes via weighted random sampling ---
    archetype_dist = config.get("archetype_distribution", {})
    archetypes = list(archetype_dist.keys())
    weights = [archetype_dist[a] for a in archetypes]

    # Normalize weights
    total_weight = sum(weights)
    if total_weight > 0:
        weights = [w / total_weight for w in weights]

    assigned_archetypes = random.choices(archetypes, weights=weights, k=count)

    # --- 2. Generate reach_scores using power-law distribution ---
    reach_exponent = config.get("reach_exponent", 2.5)
    reach_scores = _power_law_sample(count, exponent=reach_exponent)
    # Sort descending so we can identify the "top 1%" easily
    reach_scores.sort(reverse=True)
    # Shuffle back so assignment isn't ordered
    random.shuffle(reach_scores)

    # --- 3. Generate susceptibility scores from configured range ---
    susc_min, susc_max = config.get("susceptibility_range", [0.2, 0.8])

    # Susceptibility varies by archetype
    _ARCHETYPE_SUSCEPTIBILITY_BIAS: Dict[str, float] = {
        "Skeptical": -0.25,
        "Aggressive": 0.05,
        "Helpful": -0.10,
        "Opportunistic": 0.15,
        "Neutral": 0.00,
        "Contrarian": -0.05,
        "Amplifier": 0.25,
    }

    # --- 4. Demographics ---
    age_min, age_max = config.get("age_range", [18, 55])
    gender_ratio = config.get("gender_ratio", {"male": 0.50, "female": 0.47, "other": 0.03})
    genders = list(gender_ratio.keys())
    gender_weights = [gender_ratio[g] for g in genders]
    countries = config.get("countries", ["US"])
    professions = config.get("professions", ["Professional"])
    topics_pool = config.get("topics", ["General"])
    follower_min, follower_max = config.get("follower_count_range", [10, 100000])

    mbti_types = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP",
    ]

    # --- 5. Build profiles ---
    profiles: List[OasisAgentProfile] = []

    for i in range(count):
        archetype = assigned_archetypes[i]
        reach = reach_scores[i]

        # Susceptibility: base range + archetype bias, clamped to [0, 1]
        base_susc = random.uniform(susc_min, susc_max)
        bias = _ARCHETYPE_SUSCEPTIBILITY_BIAS.get(archetype, 0.0)
        susceptibility = max(0.0, min(1.0, base_susc + bias))

        # Demographics
        age = random.randint(age_min, age_max)
        gender = random.choices(genders, weights=gender_weights, k=1)[0]
        country = random.choice(countries)
        profession = random.choice(professions)
        mbti = random.choice(mbti_types)

        # Topics: 3-6 random from pool
        num_topics = random.randint(3, min(6, len(topics_pool)))
        agent_topics = random.sample(topics_pool, num_topics)

        # Follower count from reach score
        follower_count = _follower_count_from_reach(reach, follower_min, follower_max)
        friend_count = int(follower_count * random.uniform(0.3, 1.2))
        statuses_count = random.randint(50, 5000)

        # Generate a simple name (first + last placeholder)
        first_names = [
            "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley",
            "Jamie", "Quinn", "Avery", "Cameron", "Dakota", "Drew",
            "Harper", "Sage", "Reese", "Rowan", "Blake", "Charlie",
            "Skyler", "Phoenix", "Logan", "Hayden", "Parker", "Emery",
        ]
        last_names = [
            "Smith", "Chen", "Patel", "Kim", "Santos", "Nguyen",
            "Müller", "Jackson", "Williams", "Lee", "Brown", "Davis",
            "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "White",
            "Harris", "Martin", "Garcia", "Lopez", "Clark", "Lewis",
        ]
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        username = _generate_username(name, i)

        # Bio: short version from template
        topics_str = ", ".join(agent_topics[:3])
        bio = f"{profession} | {archetype} voice | Into {topics_str}"
        if len(bio) > 160:
            bio = bio[:157] + "..."

        # Persona: full template
        persona = _PERSONA_TEMPLATES.get(archetype, _PERSONA_TEMPLATES["Neutral"]).format(
            name=name,
            age=age,
            profession=profession,
            country=country,
            topics=", ".join(agent_topics),
        )

        profile = OasisAgentProfile(
            user_id=i,
            user_name=username,
            name=name,
            bio=bio,
            persona=persona,
            karma=random.randint(100, 10000),
            friend_count=friend_count,
            follower_count=follower_count,
            statuses_count=statuses_count,
            age=age,
            gender=gender,
            mbti=mbti,
            country=country,
            profession=profession,
            interested_topics=agent_topics,
            susceptibility_score=round(susceptibility, 3),
            reach_score=round(reach, 4),
            vibe_profile=archetype,
        )

        profiles.append(profile)

    logger.info(
        f"Generated {len(profiles)} profiles: "
        f"top-1% reach > {sorted(reach_scores, reverse=True)[max(0, count // 100 - 1)]:.3f}, "
        f"archetype distribution: {_count_archetypes(profiles)}"
    )

    return profiles


def generate_social_graph(
    profiles: List[OasisAgentProfile],
    avg_edges_per_node: int = 10,
    seed: Optional[int] = None,
) -> List[Tuple[int, int]]:
    """
    Generate a social graph (follow relationships) using a Barabási–Albert model.

    High reach_score agents naturally accumulate more followers, creating
    realistic hub-and-spoke network topology.

    Args:
        profiles: List of agent profiles
        avg_edges_per_node: Average number of edges per new node (BA model 'm' parameter)
        seed: Optional random seed

    Returns:
        List of (follower_id, followed_id) tuples
    """
    if seed is not None:
        random.seed(seed)

    n = len(profiles)
    if n < 2:
        return []

    m = min(avg_edges_per_node, n - 1)

    # Initialize with a fully connected core of m+1 nodes (seeded by top reach)
    sorted_by_reach = sorted(range(n), key=lambda i: profiles[i].reach_score, reverse=True)
    core_nodes = sorted_by_reach[:m + 1]

    edges: List[Tuple[int, int]] = []
    degree: Dict[int, int] = {node_id: 0 for node_id in range(n)}

    # Fully connect the core
    for i, a in enumerate(core_nodes):
        for b in core_nodes[i + 1:]:
            edges.append((a, b))
            edges.append((b, a))
            degree[a] += 1
            degree[b] += 1

    # Set of nodes already in the graph
    in_graph = set(core_nodes)

    # Add remaining nodes using preferential attachment
    remaining = [i for i in range(n) if i not in in_graph]
    random.shuffle(remaining)

    for new_node in remaining:
        # Bias attachment probability by both degree AND reach_score
        candidates = list(in_graph)
        weights = []
        for c in candidates:
            # Preferential attachment: degree + reach_score bonus
            w = (degree[c] + 1) * (1.0 + profiles[c].reach_score * 5.0)
            weights.append(w)

        # Select m unique targets
        total_w = sum(weights)
        if total_w == 0:
            targets = random.sample(candidates, min(m, len(candidates)))
        else:
            probs = [w / total_w for w in weights]
            # Weighted sampling without replacement
            targets: List[int] = []
            cand_copy = list(zip(candidates, probs))
            for _ in range(min(m, len(candidates))):
                if not cand_copy:
                    break
                chosen_idx = _weighted_choice([p for _, p in cand_copy])
                chosen_node = cand_copy[chosen_idx][0]
                targets.append(chosen_node)
                cand_copy.pop(chosen_idx)
                # Re-normalize
                remaining_w = sum(p for _, p in cand_copy)
                if remaining_w > 0:
                    cand_copy = [(c, p / remaining_w) for c, p in cand_copy]

        for target in targets:
            edges.append((new_node, target))  # new_node follows target
            degree[new_node] += 1
            degree[target] += 1

        in_graph.add(new_node)

    logger.info(
        f"Generated social graph: {n} nodes, {len(edges)} edges, "
        f"avg_degree={sum(degree.values()) / max(n, 1):.1f}"
    )

    return edges


def _weighted_choice(probabilities: List[float]) -> int:
    """Select an index from a probability distribution."""
    r = random.random()
    cumulative = 0.0
    for i, p in enumerate(probabilities):
        cumulative += p
        if r <= cumulative:
            return i
    return len(probabilities) - 1


def _count_archetypes(profiles: List[OasisAgentProfile]) -> Dict[str, int]:
    """Count agents per archetype for logging."""
    counts: Dict[str, int] = {}
    for p in profiles:
        counts[p.vibe_profile] = counts.get(p.vibe_profile, 0) + 1
    return counts


def get_available_subcultures() -> List[Dict[str, str]]:
    """Return a list of available subculture keys and names."""
    subcultures = _load_subcultures()
    return [
        {"key": key, "name": config.get("name", key), "description": config.get("description", "")}
        for key, config in subcultures.items()
    ]
