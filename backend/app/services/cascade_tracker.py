"""
Viral Cascade Tracker

Tracks per-post information cascades through the agent network.
Calculates R0 (basic reproduction number), cascade depth/breadth,
and sentiment drift as posts propagate through the population.

This is the core analytics engine for the "Social Media Wind Tunnel."
It processes engagement events emitted by the simulation loop and
maintains a real-time cascade graph for each seed post.
"""

import json
import math
import os
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger('viral.cascade_tracker')


class EngagementType(str, Enum):
    """Types of engagement that propagate cascades."""
    LIKE = "like"
    REPOST = "repost"
    QUOTE = "quote"
    REPLY = "reply"
    VIEW = "view"


@dataclass
class EngagementEvent:
    """A single engagement action in the cascade."""
    agent_id: int
    action_type: EngagementType
    timestamp: float  # Simulated time (seconds from sim start)
    round_number: int
    # Who exposed this agent to the content (None = organic/feed discovery)
    source_agent_id: Optional[int] = None
    # For QUOTE type: the mutated content
    mutated_content: Optional[str] = None
    # Sentiment of the engagement (-1.0 to 1.0)
    sentiment: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "action_type": self.action_type.value,
            "timestamp": self.timestamp,
            "round_number": self.round_number,
            "source_agent_id": self.source_agent_id,
            "mutated_content": self.mutated_content,
            "sentiment": self.sentiment,
        }


@dataclass
class CascadeNode:
    """A node in the cascade tree — represents one agent's engagement."""
    agent_id: int
    depth: int  # Hops from the original post
    event: EngagementEvent
    children: List['CascadeNode'] = field(default_factory=list)


@dataclass
class PostCascade:
    """
    Complete cascade metadata for a single seed post.

    Tracks how the post spreads through the network, including:
    - The cascade tree (who spread to whom)
    - R0 (basic reproduction number)
    - Engagement counts by type
    - Sentiment drift over time
    """
    post_id: str
    original_author_id: int
    original_content: str
    created_at_round: int
    created_at_timestamp: float

    # Cascade tree — maps agent_id → CascadeNode
    _nodes: Dict[int, CascadeNode] = field(default_factory=dict, repr=False)

    # Flat event log for serialization
    events: List[EngagementEvent] = field(default_factory=list)

    # Engagement counts
    like_count: int = 0
    repost_count: int = 0
    quote_count: int = 0
    reply_count: int = 0
    view_count: int = 0

    # Max cascade depth reached
    max_depth: int = 0

    # Set of unique agents who engaged
    _engaged_agents: Set[int] = field(default_factory=set, repr=False)

    # Sentiment timeline: round_number → aggregate sentiment
    _sentiment_by_round: Dict[int, List[float]] = field(default_factory=dict, repr=False)

    # Content mutations: list of (agent_id, mutated_content, depth)
    mutations: List[Dict[str, Any]] = field(default_factory=list)

    def record_engagement(self, event: EngagementEvent, cascade_depth: int = 0) -> None:
        """
        Record a new engagement event in this cascade.

        Args:
            event: The engagement event
            cascade_depth: How many hops from the original post
        """
        self.events.append(event)
        self._engaged_agents.add(event.agent_id)

        # Update engagement counts
        if event.action_type == EngagementType.LIKE:
            self.like_count += 1
        elif event.action_type == EngagementType.REPOST:
            self.repost_count += 1
        elif event.action_type == EngagementType.QUOTE:
            self.quote_count += 1
            if event.mutated_content:
                self.mutations.append({
                    "agent_id": event.agent_id,
                    "content": event.mutated_content,
                    "depth": cascade_depth,
                    "round": event.round_number,
                })
        elif event.action_type == EngagementType.REPLY:
            self.reply_count += 1
        elif event.action_type == EngagementType.VIEW:
            self.view_count += 1

        # Track max depth
        if cascade_depth > self.max_depth:
            self.max_depth = cascade_depth

        # Build/update cascade tree
        node = CascadeNode(
            agent_id=event.agent_id,
            depth=cascade_depth,
            event=event,
        )
        self._nodes[event.agent_id] = node

        # Link to parent node
        if event.source_agent_id is not None and event.source_agent_id in self._nodes:
            parent = self._nodes[event.source_agent_id]
            parent.children.append(node)

        # Track sentiment by round
        if event.round_number not in self._sentiment_by_round:
            self._sentiment_by_round[event.round_number] = []
        self._sentiment_by_round[event.round_number].append(event.sentiment)

    @property
    def total_engagements(self) -> int:
        """Total number of engagement events (excluding views)."""
        return self.like_count + self.repost_count + self.quote_count + self.reply_count

    @property
    def unique_engaged_agents(self) -> int:
        """Number of unique agents who engaged."""
        return len(self._engaged_agents)

    @property
    def r0(self) -> float:
        """
        Calculate R0: the basic reproduction number.

        R0 = average number of secondary engagements per engaging agent.
        An R0 > 1.0 means the cascade is growing; < 1.0 means it's dying.

        Only considers "spreading" actions (reposts, quotes, replies)
        since likes don't directly propagate content to new agents.
        """
        spreading_events = [
            e for e in self.events
            if e.action_type in (EngagementType.REPOST, EngagementType.QUOTE, EngagementType.REPLY)
        ]

        if not spreading_events:
            return 0.0

        # Count how many secondary spreads each agent caused
        spread_counts: Dict[int, int] = {}
        for event in spreading_events:
            if event.source_agent_id is not None:
                spread_counts[event.source_agent_id] = (
                    spread_counts.get(event.source_agent_id, 0) + 1
                )

        if not spread_counts:
            # No secondary spreads — all from original author
            return float(len(spreading_events))

        # R0 = total secondary spreads / number of agents who spread
        return sum(spread_counts.values()) / len(spread_counts)

    @property
    def sentiment_drift(self) -> float:
        """
        Calculate sentiment drift: rate of change in aggregate sentiment.

        Positive drift = sentiment getting more positive over time.
        Negative drift = sentiment souring as cascade progresses.

        Uses linear regression slope over the round-aggregated sentiment.
        """
        if len(self._sentiment_by_round) < 2:
            return 0.0

        # Calculate average sentiment per round
        rounds = sorted(self._sentiment_by_round.keys())
        avg_sentiments = []
        for r in rounds:
            values = self._sentiment_by_round[r]
            avg_sentiments.append(sum(values) / len(values))

        # Simple linear regression slope
        n = len(rounds)
        sum_x = sum(rounds)
        sum_y = sum(avg_sentiments)
        sum_xy = sum(r * s for r, s in zip(rounds, avg_sentiments))
        sum_x2 = sum(r * r for r in rounds)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return round(slope, 4)

    def get_sentiment_timeline(self) -> List[Dict[str, Any]]:
        """Get sentiment aggregated by round for charting."""
        timeline = []
        for r in sorted(self._sentiment_by_round.keys()):
            values = self._sentiment_by_round[r]
            positive = sum(1 for v in values if v > 0.1)
            negative = sum(1 for v in values if v < -0.1)
            neutral = len(values) - positive - negative
            avg = sum(values) / len(values)
            timeline.append({
                "round": r,
                "avg_sentiment": round(avg, 3),
                "positive_count": positive,
                "negative_count": negative,
                "neutral_count": neutral,
                "total_engagements": len(values),
            })
        return timeline

    def get_cascade_breadth(self) -> Dict[int, int]:
        """Get number of agents at each cascade depth level."""
        breadth: Dict[int, int] = {}
        for node in self._nodes.values():
            breadth[node.depth] = breadth.get(node.depth, 0) + 1
        return breadth

    def get_cascade_tree(self) -> List[Dict[str, Any]]:
        """
        Get the cascade tree as a flat list of edges for visualization.
        Each entry is {source, target, action_type, depth, round}.
        """
        edges = []
        for node in self._nodes.values():
            if node.event.source_agent_id is not None:
                edges.append({
                    "source": node.event.source_agent_id,
                    "target": node.agent_id,
                    "action_type": node.event.action_type.value,
                    "depth": node.depth,
                    "round": node.event.round_number,
                    "sentiment": node.event.sentiment,
                })
        return edges

    def to_dict(self) -> Dict[str, Any]:
        """Serialize cascade data for API responses."""
        return {
            "post_id": self.post_id,
            "original_author_id": self.original_author_id,
            "original_content": self.original_content,
            "created_at_round": self.created_at_round,
            "total_engagements": self.total_engagements,
            "unique_agents": self.unique_engaged_agents,
            "like_count": self.like_count,
            "repost_count": self.repost_count,
            "quote_count": self.quote_count,
            "reply_count": self.reply_count,
            "view_count": self.view_count,
            "max_depth": self.max_depth,
            "r0": round(self.r0, 2),
            "sentiment_drift": self.sentiment_drift,
            "cascade_breadth": self.get_cascade_breadth(),
            "sentiment_timeline": self.get_sentiment_timeline(),
            "mutations": self.mutations,
        }


class CascadeTracker:
    """
    Manages cascades for all posts in a simulation run.

    The tracker is initialized at simulation start and receives
    engagement events from the simulation loop. It maintains
    cascade state for each seed post and provides aggregate metrics.
    """

    def __init__(self, simulation_id: str, output_dir: Optional[str] = None):
        self.simulation_id = simulation_id
        self.output_dir = output_dir

        # Active cascades: post_id → PostCascade
        self._cascades: Dict[str, PostCascade] = {}

        # Global metrics tracked per round
        self._round_metrics: List[Dict[str, Any]] = []

        logger.info(f"CascadeTracker initialized for simulation {simulation_id}")

    def register_seed_post(
        self,
        post_id: str,
        author_id: int,
        content: str,
        round_number: int,
        timestamp: float = 0.0,
    ) -> PostCascade:
        """Register a new seed post to track its cascade."""
        cascade = PostCascade(
            post_id=post_id,
            original_author_id=author_id,
            original_content=content,
            created_at_round=round_number,
            created_at_timestamp=timestamp,
        )
        self._cascades[post_id] = cascade
        logger.debug(f"Registered seed post {post_id} by agent {author_id}")
        return cascade

    def record_engagement(
        self,
        post_id: str,
        agent_id: int,
        action_type: EngagementType,
        round_number: int,
        timestamp: float = 0.0,
        source_agent_id: Optional[int] = None,
        mutated_content: Optional[str] = None,
        sentiment: float = 0.0,
        cascade_depth: int = 0,
    ) -> None:
        """
        Record an engagement event for a tracked post.

        Args:
            post_id: ID of the post being engaged with
            agent_id: ID of the engaging agent
            action_type: Type of engagement
            round_number: Current simulation round
            timestamp: Simulated timestamp
            source_agent_id: Agent who exposed this agent to the content
            mutated_content: For QUOTE type, the rewritten content
            sentiment: Sentiment of this engagement (-1.0 to 1.0)
            cascade_depth: Hops from the original post
        """
        cascade = self._cascades.get(post_id)
        if not cascade:
            logger.warning(f"No cascade registered for post {post_id}")
            return

        event = EngagementEvent(
            agent_id=agent_id,
            action_type=action_type,
            timestamp=timestamp,
            round_number=round_number,
            source_agent_id=source_agent_id,
            mutated_content=mutated_content,
            sentiment=sentiment,
        )

        cascade.record_engagement(event, cascade_depth)

    def get_cascade(self, post_id: str) -> Optional[PostCascade]:
        """Get cascade data for a specific post."""
        return self._cascades.get(post_id)

    def get_all_cascades(self) -> Dict[str, PostCascade]:
        """Get all tracked cascades."""
        return self._cascades

    def get_top_cascades(self, limit: int = 10) -> List[PostCascade]:
        """Get the top cascades by total engagement count."""
        sorted_cascades = sorted(
            self._cascades.values(),
            key=lambda c: c.total_engagements,
            reverse=True,
        )
        return sorted_cascades[:limit]

    def get_global_r0(self) -> float:
        """Calculate the global average R0 across all active cascades."""
        active = [c for c in self._cascades.values() if c.total_engagements > 0]
        if not active:
            return 0.0
        return sum(c.r0 for c in active) / len(active)

    def get_global_sentiment(self) -> float:
        """Calculate the global average sentiment across all cascades."""
        all_sentiments = []
        for cascade in self._cascades.values():
            for event in cascade.events:
                if event.action_type != EngagementType.VIEW:
                    all_sentiments.append(event.sentiment)
        if not all_sentiments:
            return 0.0
        return sum(all_sentiments) / len(all_sentiments)

    def snapshot_round_metrics(self, round_number: int) -> Dict[str, Any]:
        """
        Take a snapshot of aggregate metrics at the end of a round.
        Called by the simulation loop after each round completes.
        """
        active_cascades = [c for c in self._cascades.values() if c.total_engagements > 0]

        metrics = {
            "round": round_number,
            "total_cascades": len(self._cascades),
            "active_cascades": len(active_cascades),
            "global_r0": round(self.get_global_r0(), 2),
            "global_sentiment": round(self.get_global_sentiment(), 3),
            "total_engagements": sum(c.total_engagements for c in self._cascades.values()),
            "total_unique_agents": len(
                set().union(*(c._engaged_agents for c in self._cascades.values()))
                if self._cascades else set()
            ),
            "top_cascade": None,
        }

        if active_cascades:
            top = max(active_cascades, key=lambda c: c.total_engagements)
            metrics["top_cascade"] = {
                "post_id": top.post_id,
                "engagements": top.total_engagements,
                "r0": round(top.r0, 2),
                "depth": top.max_depth,
            }

        self._round_metrics.append(metrics)
        return metrics

    def get_round_metrics_timeline(self) -> List[Dict[str, Any]]:
        """Get the full timeline of round metrics for charting."""
        return self._round_metrics

    def save_to_file(self, filepath: Optional[str] = None) -> str:
        """
        Save cascade data to a JSONL file.

        Args:
            filepath: Output path. If None, uses output_dir/cascades.jsonl

        Returns:
            The path the data was saved to.
        """
        if filepath is None:
            if self.output_dir:
                filepath = os.path.join(self.output_dir, "cascades.jsonl")
            else:
                filepath = f"cascades_{self.simulation_id}.jsonl"

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for cascade in self._cascades.values():
                    line = json.dumps(cascade.to_dict(), ensure_ascii=False)
                    f.write(line + '\n')

            # Also save round metrics
            metrics_path = filepath.replace('.jsonl', '_metrics.jsonl')
            with open(metrics_path, 'w', encoding='utf-8') as f:
                for metrics in self._round_metrics:
                    line = json.dumps(metrics, ensure_ascii=False)
                    f.write(line + '\n')

            logger.info(f"Saved {len(self._cascades)} cascades to {filepath}")
            return filepath

        except OSError as e:
            logger.error(f"Failed to save cascades: {e}")
            raise

    def to_api_response(self) -> Dict[str, Any]:
        """Format all cascade data for the API response."""
        return {
            "simulation_id": self.simulation_id,
            "global_r0": round(self.get_global_r0(), 2),
            "global_sentiment": round(self.get_global_sentiment(), 3),
            "total_cascades": len(self._cascades),
            "total_engagements": sum(c.total_engagements for c in self._cascades.values()),
            "cascades": [c.to_dict() for c in self.get_top_cascades(20)],
            "round_metrics": self._round_metrics,
        }
