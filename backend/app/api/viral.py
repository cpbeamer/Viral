"""
Viral Dashboard API Blueprint

Endpoints for the real-time cascade observation dashboard:
- GET  /api/viral/cascades/<simulation_id> — Current cascade data
- POST /api/viral/inject — Inject a seed post into a running simulation
- POST /api/viral/tuning — Adjust population parameters in real-time
- POST /api/viral/preset — Apply a scenario preset
- GET  /api/viral/subcultures — List available subculture configs
"""

import uuid
from flask import request, jsonify

from . import viral_bp
from ..services.cascade_tracker import CascadeTracker, EngagementType
from ..services.population_generator import get_available_subcultures
from ..utils.logger import get_logger

logger = get_logger('viral.api')

# In-memory tracker registry (keyed by simulation_id)
# In production, this would be backed by Redis or a database
_trackers: dict = {}


def get_or_create_tracker(simulation_id: str) -> CascadeTracker:
    """Get tracker for a simulation, creating one if it doesn't exist."""
    if simulation_id not in _trackers:
        _trackers[simulation_id] = CascadeTracker(simulation_id)
    return _trackers[simulation_id]


@viral_bp.route('/api/viral/cascades/<simulation_id>', methods=['GET'])
def get_cascades(simulation_id):
    """
    Get current cascade data for the Viral Dashboard.

    Returns global R0, sentiment, top cascades, and round metrics timeline.
    """
    try:
        tracker = get_or_create_tracker(simulation_id)
        return jsonify(tracker.to_api_response())
    except Exception as e:
        logger.error(f"Error fetching cascades for {simulation_id}: {e}")
        return jsonify({"error": str(e)}), 500


@viral_bp.route('/api/viral/inject', methods=['POST'])
def inject_post():
    """
    Inject a seed post into a running simulation.

    Body:
        simulation_id: str
        content: str
        reach: float (0-1)
        vibe: str
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        simulation_id = data.get('simulation_id')
        content = data.get('content', '').strip()
        reach = float(data.get('reach', 0.5))
        vibe = data.get('vibe', 'Neutral')

        if not simulation_id or not content:
            return jsonify({"error": "simulation_id and content are required"}), 400

        tracker = get_or_create_tracker(simulation_id)

        # Create a new seed post in the tracker
        post_id = f"inject_{uuid.uuid4().hex[:8]}"
        metrics = tracker.get_round_metrics_timeline()
        current_round = metrics[-1]['round'] if metrics else 0

        tracker.register_seed_post(
            post_id=post_id,
            author_id=-1,  # -1 = injected by operator
            content=content,
            round_number=current_round,
        )

        logger.info(
            f"Injected seed post '{post_id}' into simulation {simulation_id}: "
            f"reach={reach}, vibe={vibe}"
        )

        return jsonify({
            "success": True,
            "post_id": post_id,
            "message": f"Post injected at round {current_round}",
        })

    except Exception as e:
        logger.error(f"Error injecting post: {e}")
        return jsonify({"error": str(e)}), 500


@viral_bp.route('/api/viral/tuning', methods=['POST'])
def apply_tuning():
    """
    Apply real-time parameter tuning to a running simulation.

    Body:
        simulation_id: str
        susceptibility_multiplier: float
        echo_chamber_weight: float
        feed_noise: float
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({"error": "simulation_id is required"}), 400

        # Store tuning config (will be read by the simulation loop)
        tuning = {
            'susceptibility_multiplier': float(data.get('susceptibility_multiplier', 1.0)),
            'echo_chamber_weight': float(data.get('echo_chamber_weight', 0.20)),
            'feed_noise': float(data.get('feed_noise', 0.10)),
        }

        # Store in tracker metadata for the simulation loop to pick up
        tracker = get_or_create_tracker(simulation_id)
        tracker._tuning = tuning

        logger.info(f"Applied tuning to {simulation_id}: {tuning}")

        return jsonify({
            "success": True,
            "tuning": tuning,
        })

    except Exception as e:
        logger.error(f"Error applying tuning: {e}")
        return jsonify({"error": str(e)}), 500


@viral_bp.route('/api/viral/preset', methods=['POST'])
def apply_preset():
    """
    Apply a scenario preset to a running simulation.

    Body:
        simulation_id: str
        preset: str (fud_storm, echo_bubble, fact_check, viral_bomb)
        config: dict
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        simulation_id = data.get('simulation_id')
        preset = data.get('preset')
        config = data.get('config', {})

        if not simulation_id or not preset:
            return jsonify({"error": "simulation_id and preset are required"}), 400

        # Apply preset config as tuning
        tracker = get_or_create_tracker(simulation_id)
        tracker._tuning = config

        logger.info(f"Applied preset '{preset}' to {simulation_id}: {config}")

        return jsonify({
            "success": True,
            "preset": preset,
            "config": config,
        })

    except Exception as e:
        logger.error(f"Error applying preset: {e}")
        return jsonify({"error": str(e)}), 500


@viral_bp.route('/api/viral/subcultures', methods=['GET'])
def list_subcultures():
    """List all available subculture configurations."""
    try:
        return jsonify(get_available_subcultures())
    except Exception as e:
        logger.error(f"Error listing subcultures: {e}")
        return jsonify({"error": str(e)}), 500
