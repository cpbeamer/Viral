"""
Tests for the Viral Feed Algorithm, Mutation Engine, and Sentiment Analyzer.
"""

import sys
import os
import random

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.feed_algorithm import (
    compute_feed,
    should_agent_engage,
    FeedPost,
    FeedConfig,
)
from app.services.mutation_engine import (
    mutate_content_template,
    build_llm_mutation_prompt,
    parse_llm_mutation,
    get_mutation_genome,
)
from app.services.sentiment_analyzer import (
    analyze_sentiment,
    batch_analyze_sentiment,
    get_round_sentiment_summary,
)


class TestFeedAlgorithm:
    """Tests for the feed ranking algorithm."""

    def _make_posts(self, count: int, current_round: int = 5) -> list:
        posts = []
        for i in range(count):
            posts.append(FeedPost(
                post_id=f"p_{i}",
                author_id=i + 10,
                content=f"Post content {i}",
                created_round=current_round - i,  # Older posts have lower round
                like_count=i * 2,
                author_reach=0.1 + i * 0.05,
                author_vibe="Neutral",
                author_topics=["tech", "science"],
            ))
        return posts

    def test_feed_returns_posts(self):
        """Feed should return a non-empty list of posts."""
        posts = self._make_posts(10)
        config = FeedConfig()
        feed = compute_feed(
            agent_id=0, agent_topics=["tech"], agent_vibe="Neutral",
            agent_susceptibility=0.5, current_round=5,
            available_posts=posts, following=[], config=config,
        )
        assert len(feed) > 0

    def test_feed_excludes_own_posts(self):
        """Agent should not see their own posts in the feed."""
        posts = [FeedPost(
            post_id="p1", author_id=0, content="My post",
            created_round=5, author_topics=["tech"],
        )]
        config = FeedConfig()
        feed = compute_feed(
            agent_id=0, agent_topics=["tech"], agent_vibe="Neutral",
            agent_susceptibility=0.5, current_round=5,
            available_posts=posts, following=[], config=config,
        )
        assert len(feed) == 0

    def test_feed_respects_size_limit(self):
        """Feed should not exceed configured feed_size."""
        posts = self._make_posts(50)
        config = FeedConfig(feed_size=10)
        feed = compute_feed(
            agent_id=0, agent_topics=["tech"], agent_vibe="Neutral",
            agent_susceptibility=0.5, current_round=5,
            available_posts=posts, following=[], config=config,
        )
        assert len(feed) <= 10

    def test_recent_posts_rank_higher(self):
        """More recent posts should generally rank higher."""
        random.seed(42)
        config = FeedConfig(recency_weight=0.9, popularity_weight=0.0,
                           relevance_weight=0.0, echo_chamber_weight=0.0,
                           noise_factor=0.0)
        posts = [
            FeedPost(post_id="old", author_id=1, content="Old", created_round=1,
                    author_topics=["general"]),
            FeedPost(post_id="new", author_id=2, content="New", created_round=5,
                    author_topics=["general"]),
        ]
        feed = compute_feed(
            agent_id=0, agent_topics=["general"], agent_vibe="Neutral",
            agent_susceptibility=0.5, current_round=5,
            available_posts=posts, following=[], config=config,
        )
        assert feed[0].post_id == "new"

    def test_popular_posts_rank_higher(self):
        """More popular posts should rank higher when popularity weight is high."""
        random.seed(42)
        config = FeedConfig(recency_weight=0.0, popularity_weight=0.9,
                           relevance_weight=0.0, echo_chamber_weight=0.0,
                           noise_factor=0.0)
        posts = [
            FeedPost(post_id="unpopular", author_id=1, content="Low",
                    created_round=5, like_count=0, author_topics=["any"]),
            FeedPost(post_id="popular", author_id=2, content="High",
                    created_round=5, like_count=100, repost_count=50,
                    author_topics=["any"]),
        ]
        feed = compute_feed(
            agent_id=0, agent_topics=["any"], agent_vibe="Neutral",
            agent_susceptibility=0.5, current_round=5,
            available_posts=posts, following=[], config=config,
        )
        assert feed[0].post_id == "popular"

    def test_following_boost(self):
        """Posts from followed agents should get a relevance boost."""
        random.seed(42)
        config = FeedConfig(
            recency_weight=0.0, popularity_weight=0.0,
            relevance_weight=0.9, echo_chamber_weight=0.0,
            noise_factor=0.0,
        )
        posts = [
            FeedPost(post_id="stranger", author_id=99, content="Stranger post",
                    created_round=5, author_topics=["cooking"]),
            FeedPost(post_id="friend", author_id=42, content="Friend post",
                    created_round=5, author_topics=["cooking"]),
        ]
        feed = compute_feed(
            agent_id=0, agent_topics=["tech"], agent_vibe="Neutral",
            agent_susceptibility=0.5, current_round=5,
            available_posts=posts, following=[42], config=config,
        )
        # Friend's post should rank higher due to following boost
        assert feed[0].post_id == "friend"


class TestEngagementDecision:
    """Tests for susceptibility-based engagement decisions."""

    def test_high_susceptibility_engages_more(self):
        """Agents with high susceptibility should engage more often."""
        random.seed(42)
        post = FeedPost(
            post_id="p1", author_id=1, content="Test",
            created_round=5, like_count=10,
        )

        high_susc_engages = sum(
            1 for _ in range(1000)
            if should_agent_engage(0.95, "Amplifier", post)[0]
        )
        low_susc_engages = sum(
            1 for _ in range(1000)
            if should_agent_engage(0.05, "Skeptical", post)[0]
        )

        assert high_susc_engages > low_susc_engages

    def test_amplifiers_repost_more(self):
        """Amplifiers should choose 'repost' more often than other types."""
        random.seed(42)
        post = FeedPost(post_id="p1", author_id=1, content="Test", created_round=5)
        repost_count = 0
        total = 0
        for _ in range(1000):
            engaged, action = should_agent_engage(0.8, "Amplifier", post)
            if engaged:
                total += 1
                if action == "repost":
                    repost_count += 1

        repost_ratio = repost_count / max(total, 1)
        assert repost_ratio > 0.30  # Amplifiers should repost >30% of engagements

    def test_skeptics_quote_more(self):
        """Skeptics should quote-tweet and reply more than repost."""
        random.seed(42)
        post = FeedPost(post_id="p1", author_id=1, content="Test", created_round=5)
        quote_reply_count = 0
        total = 0
        for _ in range(1000):
            engaged, action = should_agent_engage(0.5, "Skeptical", post)
            if engaged:
                total += 1
                if action in ("quote", "reply"):
                    quote_reply_count += 1

        ratio = quote_reply_count / max(total, 1)
        assert ratio > 0.50  # Skeptics should quote/reply >50% of the time

    def test_returns_valid_action_types(self):
        """Engagement actions should be valid strings."""
        random.seed(42)
        post = FeedPost(post_id="p1", author_id=1, content="Test", created_round=5)
        valid_actions = {"like", "repost", "quote", "reply", None}
        for _ in range(100):
            _, action = should_agent_engage(0.5, "Neutral", post)
            assert action in valid_actions


class TestMutationEngine:
    """Tests for the mutation engine."""

    def test_template_mutation_returns_content(self):
        """Template mutation should return non-empty mutated content."""
        result = mutate_content_template("Original post about crypto markets", "Aggressive")
        assert result["mutated_content"]
        assert len(result["mutated_content"]) > 0

    def test_template_mutation_distance_in_range(self):
        """Mutation distance should be between 0 and 1."""
        result = mutate_content_template("Test content here", "Skeptical")
        assert 0.0 <= result["mutation_distance"] <= 1.0

    def test_template_preserves_original_context(self):
        """Mutated content should contain reference to the original."""
        original = "Breaking: massive data breach at TechCorp"
        result = mutate_content_template(original, "Helpful")
        # Template wraps the original, so some of it should appear
        assert "data breach" in result["mutated_content"].lower() or "techcorp" in result["mutated_content"].lower()

    def test_each_vibe_has_templates(self):
        """Every vibe profile should produce a valid mutation."""
        vibes = ["Skeptical", "Aggressive", "Helpful", "Opportunistic",
                 "Neutral", "Contrarian", "Amplifier"]
        for vibe in vibes:
            result = mutate_content_template("Test post content", vibe)
            assert result["mutated_content"], f"No mutation for vibe {vibe}"
            assert result["method"] == "template"

    def test_llm_prompt_builder(self):
        """LLM prompt should include agent details and original content."""
        prompt = build_llm_mutation_prompt(
            original_content="Crypto is crashing today!",
            username="crypto_whale_42",
            vibe_profile="Opportunistic",
            bio="Day trader | 10x or bust",
            persona="A 28-year-old crypto trader who lives and breathes the market.",
        )
        assert "crypto_whale_42" in prompt
        assert "Opportunistic" in prompt
        assert "Crypto is crashing" in prompt

    def test_parse_llm_mutation(self):
        """parse_llm_mutation should compute mutation distance."""
        result = parse_llm_mutation(
            "Original content about markets",
            "This is my hot take: markets are changing!",
            "Aggressive",
        )
        assert result["mutated_content"] == "This is my hot take: markets are changing!"
        assert 0.0 <= result["mutation_distance"] <= 1.0
        assert result["method"] == "llm"

    def test_mutation_genome_empty(self):
        """Empty mutations list should return zero genome."""
        genome = get_mutation_genome([])
        assert genome["total_mutations"] == 0

    def test_mutation_genome_tracks_depth(self):
        """Genome should track mutations by depth."""
        mutations = [
            {"mutation_distance": 0.3, "depth": 1, "sentiment_shift": -0.1},
            {"mutation_distance": 0.5, "depth": 1, "sentiment_shift": -0.2},
            {"mutation_distance": 0.7, "depth": 2, "sentiment_shift": -0.3},
        ]
        genome = get_mutation_genome(mutations)
        assert genome["total_mutations"] == 3
        assert genome["max_depth"] == 2
        assert len(genome["sentiment_trajectory"]) == 2  # 2 depths


class TestSentimentAnalyzer:
    """Tests for the lexicon-based sentiment analyzer."""

    def test_positive_text(self):
        """Clearly positive text should return positive score."""
        score = analyze_sentiment("This is absolutely amazing and wonderful!")
        assert score > 0.3

    def test_negative_text(self):
        """Clearly negative text should return negative score."""
        score = analyze_sentiment("This is terrible and disgusting, the worst thing ever")
        assert score < -0.3

    def test_neutral_text(self):
        """Neutral text should return near-zero score."""
        score = analyze_sentiment("The meeting is scheduled for tomorrow at 3pm")
        assert -0.3 <= score <= 0.3

    def test_negation_flips_sentiment(self):
        """Negation words should flip sentiment direction."""
        positive = analyze_sentiment("This is great")
        negated = analyze_sentiment("This is not great")
        assert positive > 0
        assert negated < positive  # "not great" should be less positive

    def test_intensifier_amplifies(self):
        """Intensifiers should amplify sentiment magnitude."""
        normal = abs(analyze_sentiment("This is good"))
        intensified = abs(analyze_sentiment("This is extremely good"))
        assert intensified >= normal

    def test_chinese_positive(self):
        """Chinese positive words should be recognized."""
        score = analyze_sentiment("非常 棒 优秀")
        assert score > 0

    def test_chinese_negative(self):
        """Chinese negative words should be recognized."""
        score = analyze_sentiment("垃圾 差 愤怒")
        assert score < 0

    def test_batch_analyze(self):
        """Batch analysis should return one score per text."""
        texts = ["Great!", "Terrible!", "Okay"]
        scores = batch_analyze_sentiment(texts)
        assert len(scores) == 3
        assert scores[0] > 0
        assert scores[1] < 0

    def test_empty_text(self):
        """Empty text should return 0.0."""
        assert analyze_sentiment("") == 0.0

    def test_round_summary(self):
        """Round summary should categorize sentiments correctly."""
        sentiments = [0.5, 0.3, -0.5, -0.3, 0.0, 0.05]
        summary = get_round_sentiment_summary(sentiments)
        assert summary["positive_count"] == 2  # > 0.1
        assert summary["negative_count"] == 2  # < -0.1
        assert summary["neutral_count"] == 2
        assert summary["total"] == 6
