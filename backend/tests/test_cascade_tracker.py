"""
Tests for the Viral Cascade Tracker.

Tests cover:
- Seed post registration
- Engagement recording and counting
- R0 (basic reproduction number) calculation
- Cascade depth and breadth tracking
- Sentiment drift calculation
- Serialization for API responses
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.cascade_tracker import (
    CascadeTracker,
    PostCascade,
    EngagementEvent,
    EngagementType,
)


class TestPostCascade:
    """Tests for individual post cascade tracking."""

    def _make_cascade(self) -> PostCascade:
        return PostCascade(
            post_id="post_001",
            original_author_id=0,
            original_content="Test post content",
            created_at_round=1,
            created_at_timestamp=0.0,
        )

    def test_empty_cascade_metrics(self):
        """An empty cascade should have zero metrics."""
        cascade = self._make_cascade()
        assert cascade.total_engagements == 0
        assert cascade.unique_engaged_agents == 0
        assert cascade.r0 == 0.0
        assert cascade.max_depth == 0

    def test_record_like(self):
        """Recording a like should increment like_count."""
        cascade = self._make_cascade()
        event = EngagementEvent(
            agent_id=1, action_type=EngagementType.LIKE,
            timestamp=1.0, round_number=1,
        )
        cascade.record_engagement(event, cascade_depth=1)
        assert cascade.like_count == 1
        assert cascade.total_engagements == 1

    def test_record_multiple_types(self):
        """Multiple engagement types should be counted correctly."""
        cascade = self._make_cascade()
        for i, action in enumerate([EngagementType.LIKE, EngagementType.REPOST, EngagementType.QUOTE]):
            event = EngagementEvent(
                agent_id=i + 1, action_type=action,
                timestamp=float(i), round_number=1,
            )
            cascade.record_engagement(event)

        assert cascade.like_count == 1
        assert cascade.repost_count == 1
        assert cascade.quote_count == 1
        assert cascade.total_engagements == 3
        assert cascade.unique_engaged_agents == 3

    def test_cascade_depth_tracking(self):
        """Max depth should be updated as cascade spreads."""
        cascade = self._make_cascade()
        for depth in [1, 2, 3, 5]:
            event = EngagementEvent(
                agent_id=depth, action_type=EngagementType.REPOST,
                timestamp=0.0, round_number=1,
            )
            cascade.record_engagement(event, cascade_depth=depth)

        assert cascade.max_depth == 5

    def test_r0_simple(self):
        """R0 should equal secondary spreads / number of spreaders."""
        cascade = self._make_cascade()

        # Agent 0 (original) → agents 1, 2, 3 (3 secondary reposts)
        for agent_id in [1, 2, 3]:
            event = EngagementEvent(
                agent_id=agent_id, action_type=EngagementType.REPOST,
                timestamp=0.0, round_number=1,
                source_agent_id=0,
            )
            cascade.record_engagement(event, cascade_depth=1)

        # R0 = 3 secondary spreads / 1 spreader (agent 0) = 3.0
        assert cascade.r0 == 3.0

    def test_r0_multi_generation(self):
        """R0 with multiple generations of spreading."""
        cascade = self._make_cascade()

        # Generation 1: agent 0 → agents 1, 2
        for agent_id in [1, 2]:
            event = EngagementEvent(
                agent_id=agent_id, action_type=EngagementType.REPOST,
                timestamp=0.0, round_number=1, source_agent_id=0,
            )
            cascade.record_engagement(event, cascade_depth=1)

        # Generation 2: agent 1 → agents 3, 4, 5
        for agent_id in [3, 4, 5]:
            event = EngagementEvent(
                agent_id=agent_id, action_type=EngagementType.REPOST,
                timestamp=0.0, round_number=2, source_agent_id=1,
            )
            cascade.record_engagement(event, cascade_depth=2)

        # Spreaders: agent 0 (spread 2), agent 1 (spread 3)
        # Total secondary = 5, spreaders = 2 → R0 = 2.5
        assert cascade.r0 == 2.5

    def test_sentiment_drift_positive(self):
        """Sentiment drift should be positive when sentiment increases over rounds."""
        cascade = self._make_cascade()
        # Round 1: negative sentiment
        for _ in range(5):
            event = EngagementEvent(
                agent_id=1, action_type=EngagementType.LIKE,
                timestamp=0.0, round_number=1, sentiment=-0.5,
            )
            cascade.record_engagement(event)
        # Round 5: positive sentiment
        for _ in range(5):
            event = EngagementEvent(
                agent_id=2, action_type=EngagementType.LIKE,
                timestamp=0.0, round_number=5, sentiment=0.5,
            )
            cascade.record_engagement(event)

        assert cascade.sentiment_drift > 0

    def test_sentiment_drift_negative(self):
        """Sentiment drift should be negative when sentiment decreases."""
        cascade = self._make_cascade()
        for _ in range(5):
            event = EngagementEvent(
                agent_id=1, action_type=EngagementType.LIKE,
                timestamp=0.0, round_number=1, sentiment=0.5,
            )
            cascade.record_engagement(event)
        for _ in range(5):
            event = EngagementEvent(
                agent_id=2, action_type=EngagementType.LIKE,
                timestamp=0.0, round_number=5, sentiment=-0.5,
            )
            cascade.record_engagement(event)

        assert cascade.sentiment_drift < 0

    def test_mutation_tracking(self):
        """Quote-tweet mutations should be tracked."""
        cascade = self._make_cascade()
        event = EngagementEvent(
            agent_id=5, action_type=EngagementType.QUOTE,
            timestamp=0.0, round_number=2,
            mutated_content="This is my take on the original post!",
        )
        cascade.record_engagement(event, cascade_depth=1)

        assert cascade.quote_count == 1
        assert len(cascade.mutations) == 1
        assert cascade.mutations[0]["content"] == "This is my take on the original post!"

    def test_to_dict_serialization(self):
        """to_dict should include all key metrics."""
        cascade = self._make_cascade()
        event = EngagementEvent(
            agent_id=1, action_type=EngagementType.LIKE,
            timestamp=0.0, round_number=1,
        )
        cascade.record_engagement(event)

        data = cascade.to_dict()
        assert "post_id" in data
        assert "r0" in data
        assert "sentiment_drift" in data
        assert "cascade_breadth" in data
        assert data["total_engagements"] == 1

    def test_cascade_tree_edges(self):
        """get_cascade_tree should return source→target edges."""
        cascade = self._make_cascade()
        event = EngagementEvent(
            agent_id=2, action_type=EngagementType.REPOST,
            timestamp=0.0, round_number=1, source_agent_id=0,
        )
        cascade.record_engagement(event, cascade_depth=1)

        edges = cascade.get_cascade_tree()
        assert len(edges) == 1
        assert edges[0]["source"] == 0
        assert edges[0]["target"] == 2

    def test_cascade_breadth(self):
        """Breadth should count agents at each depth level."""
        cascade = self._make_cascade()
        # 2 agents at depth 1
        for aid in [1, 2]:
            event = EngagementEvent(
                agent_id=aid, action_type=EngagementType.REPOST,
                timestamp=0.0, round_number=1,
            )
            cascade.record_engagement(event, cascade_depth=1)
        # 3 agents at depth 2
        for aid in [3, 4, 5]:
            event = EngagementEvent(
                agent_id=aid, action_type=EngagementType.REPOST,
                timestamp=0.0, round_number=2,
            )
            cascade.record_engagement(event, cascade_depth=2)

        breadth = cascade.get_cascade_breadth()
        assert breadth[1] == 2
        assert breadth[2] == 3


class TestCascadeTracker:
    """Tests for the simulation-level cascade tracker."""

    def test_register_and_retrieve(self):
        """Should be able to register and retrieve cascades."""
        tracker = CascadeTracker("sim_001")
        tracker.register_seed_post("p1", 0, "Hello world", 1)

        cascade = tracker.get_cascade("p1")
        assert cascade is not None
        assert cascade.post_id == "p1"

    def test_record_engagement(self):
        """Should record engagements against registered cascades."""
        tracker = CascadeTracker("sim_001")
        tracker.register_seed_post("p1", 0, "Hello world", 1)
        tracker.record_engagement(
            "p1", agent_id=1, action_type=EngagementType.LIKE,
            round_number=1,
        )

        cascade = tracker.get_cascade("p1")
        assert cascade.like_count == 1

    def test_global_r0(self):
        """Global R0 averages across all active cascades."""
        tracker = CascadeTracker("sim_001")
        tracker.register_seed_post("p1", 0, "Post 1", 1)
        tracker.register_seed_post("p2", 0, "Post 2", 1)

        # p1: R0 = 2 (2 secondary reposts from agent 0)
        for aid in [1, 2]:
            tracker.record_engagement(
                "p1", agent_id=aid, action_type=EngagementType.REPOST,
                round_number=1, source_agent_id=0,
            )

        # p2: R0 = 1 (1 secondary repost from agent 0)
        tracker.record_engagement(
            "p2", agent_id=3, action_type=EngagementType.REPOST,
            round_number=1, source_agent_id=0,
        )

        # Global R0 = (2 + 1) / 2 = 1.5
        assert tracker.get_global_r0() == 1.5

    def test_top_cascades_sorted(self):
        """get_top_cascades should return cascades sorted by engagement."""
        tracker = CascadeTracker("sim_001")
        tracker.register_seed_post("p1", 0, "Post 1", 1)
        tracker.register_seed_post("p2", 0, "Post 2", 1)

        # p1: 1 like
        tracker.record_engagement(
            "p1", agent_id=1, action_type=EngagementType.LIKE, round_number=1,
        )

        # p2: 3 likes
        for aid in [1, 2, 3]:
            tracker.record_engagement(
                "p2", agent_id=aid, action_type=EngagementType.LIKE, round_number=1,
            )

        top = tracker.get_top_cascades(limit=2)
        assert top[0].post_id == "p2"
        assert top[0].total_engagements == 3

    def test_round_metrics_snapshot(self):
        """Snapshot should capture aggregate round metrics."""
        tracker = CascadeTracker("sim_001")
        tracker.register_seed_post("p1", 0, "Post 1", 1)
        tracker.record_engagement(
            "p1", agent_id=1, action_type=EngagementType.LIKE,
            round_number=1, sentiment=0.5,
        )

        metrics = tracker.snapshot_round_metrics(round_number=1)
        assert metrics["round"] == 1
        assert metrics["total_engagements"] == 1
        assert metrics["global_r0"] == 0.0  # No spreading, only likes
        assert metrics["global_sentiment"] == 0.5

    def test_api_response_format(self):
        """to_api_response should include all required fields."""
        tracker = CascadeTracker("sim_001")
        tracker.register_seed_post("p1", 0, "Post 1", 1)

        response = tracker.to_api_response()
        assert "simulation_id" in response
        assert "global_r0" in response
        assert "cascades" in response
        assert "round_metrics" in response
