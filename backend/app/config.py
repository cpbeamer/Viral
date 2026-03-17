"""
Configuration Management
Loads settings from the project root .env file
"""

import os
from dotenv import load_dotenv

# Load .env from project root
# Path: Viral/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # Fall back to environment variables (for production)
    load_dotenv(override=True)


class Config:
    """Viral application configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'viral-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON — disable ASCII escaping for CJK characters
    JSON_AS_ASCII = False
    
    # LLM (OpenAI-compatible format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Zep memory service
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # File uploads
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # Text processing
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50
    
    # OASIS simulation
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS platform actions
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    # --- Viral Wind Tunnel ---
    VIRAL_DEFAULT_POPULATION_SIZE = int(os.environ.get('VIRAL_DEFAULT_POPULATION_SIZE', '10000'))
    VIRAL_DEFAULT_SUBCULTURE = os.environ.get('VIRAL_DEFAULT_SUBCULTURE', 'default')
    VIRAL_LLM_ENRICHMENT_PERCENT = int(os.environ.get('VIRAL_LLM_ENRICHMENT_PERCENT', '1'))

    # Feed algorithm weights
    VIRAL_FEED_RECENCY_WEIGHT = float(os.environ.get('VIRAL_FEED_RECENCY_WEIGHT', '0.30'))
    VIRAL_FEED_POPULARITY_WEIGHT = float(os.environ.get('VIRAL_FEED_POPULARITY_WEIGHT', '0.25'))
    VIRAL_FEED_RELEVANCE_WEIGHT = float(os.environ.get('VIRAL_FEED_RELEVANCE_WEIGHT', '0.25'))
    VIRAL_FEED_ECHO_WEIGHT = float(os.environ.get('VIRAL_FEED_ECHO_WEIGHT', '0.20'))
    VIRAL_FEED_NOISE = float(os.environ.get('VIRAL_FEED_NOISE', '0.10'))

    # Dashboard polling interval (ms)
    VIRAL_DASHBOARD_POLL_MS = int(os.environ.get('VIRAL_DASHBOARD_POLL_MS', '3000'))

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY not configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY not configured")
        return errors

