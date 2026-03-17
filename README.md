<div align="center">

# 🧬 Viral — Social Media Wind Tunnel

**Predict virality before it happens.**

A simulation engine that models how information spreads, mutates, and goes viral across 10,000 AI agents with distinct personalities, susceptibilities, and behavioral archetypes.

[![Tests](https://img.shields.io/badge/tests-71%20passed-brightgreen?style=flat-square)]()
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![Vue](https://img.shields.io/badge/Vue.js-3-4FC08D?style=flat-square&logo=vue.js&logoColor=white)]()
[![D3](https://img.shields.io/badge/D3.js-7-F9A03C?style=flat-square&logo=d3.js&logoColor=white)]()
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square)]()

</div>

---

## What is Viral?

Viral is a **Social Media Wind Tunnel** — an agent-based simulation that predicts how a piece of content will spread through a social network. Instead of guessing whether your post, press release, or PR crisis will go viral, you can **simulate it first**.

Built on top of the [OASIS](https://github.com/camel-ai/oasis) multi-agent framework from CAMEL-AI, Viral extends the base engine with:

- **10,000 agents** with unique susceptibility scores, reach levels, and behavioral archetypes
- **Information cascade tracking** with R₀ (reproduction number) — the same metric epidemiologists use
- **Narrative mutation** — agents don't just share content, they *reframe* it based on their personality
- **Real-time dashboard** with D3.js visualizations and "God Mode" controls

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  VIRAL DASHBOARD                     │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ R₀ Gauge │  │  Sentiment   │  │   God Mode    │  │
│  │ Timeline │  │  Heatmap     │  │   Controls    │  │
│  └──────────┘  └──────────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────┤
│                   FLASK API                          │
│  /api/viral/cascades  /inject  /tuning  /preset      │
├─────────────────────────────────────────────────────┤
│               SIMULATION ENGINE                      │
│  ┌────────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │   Feed     │ │ Cascade  │ │    Mutation        │  │
│  │ Algorithm  │ │ Tracker  │ │    Engine          │  │
│  └────────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│              POPULATION LAYER                        │
│  10K agents · Power-law reach · 7 archetypes         │
│  Barabási-Albert social graph · 4 subcultures        │
└─────────────────────────────────────────────────────┘
```

## Key Concepts

### Agent Archetypes

Each agent has a **vibe profile** that determines how they engage:

| Archetype | Behavior | Typical Action |
|-----------|----------|----------------|
| **Skeptical** | Questions everything | Quote-tweets with doubt |
| **Amplifier** | Spreads everything | Reposts without comment |
| **Aggressive** | Attacks and dunks | Hostile quote-tweets |
| **Opportunistic** | Rides the wave | Trend-jacks content |
| **Helpful** | Adds context | Replies with info |
| **Contrarian** | Takes the opposite view | Contradicts the narrative |
| **Neutral** | Passive observer | Likes occasionally |

### R₀ — The Virality Score

Borrowed from epidemiology, **R₀** (basic reproduction number) measures how many secondary shares each share generates:

- **R₀ < 1.0** → Content is dying. Not reaching critical mass.
- **R₀ = 1.0–2.0** → Spreading. Each share creates 1–2 more shares.
- **R₀ > 2.0** → **Viral.** Exponential growth. PR nightmare territory.

### Subculture Presets

Pre-configured population distributions for different communities:

| Subculture | Key Traits |
|------------|------------|
| **Crypto Twitter** | High susceptibility, many amplifiers, FOMO-driven |
| **Political Junkies** | Polarized, high skepticism, aggressive debate |
| **Gen-Z Gamers** | Meme-forward, irony-heavy, short attention span |
| **Default** | Balanced mix for general-purpose simulation |

## Quick Start

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Node.js | 18+ | `node -v` |
| Python | 3.11–3.12 | `python --version` |
| uv | latest | `uv --version` |

### 1. Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required keys:**
```env
LLM_API_KEY=your-openai-or-groq-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
ZEP_API_KEY=your-zep-key
```

### 2. Install

```bash
npm run setup:all
```

### 3. Run

```bash
npm run dev
```

- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:5001
- **Dashboard:** http://localhost:3000/viral/{simulation_id}

## Dashboard

The Viral Dashboard at `/viral/:simulationId` has three tabs:

### Overview
- **R₀ Gauge** — real-time reproduction number with threshold indicator
- **Sentiment Timeline** — positive/negative drift over simulation rounds
- **Engagement Heatmap** — heat-map of engagements, R₀, and sentiment by round
- **KPI Cards** — total engagements, active cascades, max cascade depth

### Cascades
- Interactive list of top cascades ranked by engagement
- Cascade depth visualization (bar chart)
- **Narrative Mutation Viewer** — see how content transforms as it spreads

### God Mode
- **Inject Posts** — drop a new post into the simulation mid-run
- **Population Tuning** — adjust susceptibility multiplier, echo chamber strength, feed noise
- **Scenario Presets:** 🌪️ FUD Storm · 🫧 Echo Bubble · 🔍 Fact-Check Wave · 💣 Viral Bomb

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/viral/cascades/:id` | Current cascade data (R₀, sentiment, engagements) |
| `POST` | `/api/viral/inject` | Inject a seed post |
| `POST` | `/api/viral/tuning` | Adjust population parameters |
| `POST` | `/api/viral/preset` | Apply a scenario preset |
| `GET` | `/api/viral/subcultures` | List subculture configs |

## Testing

```bash
cd backend
uv run pytest tests/ -v
```

```
============================= 71 passed in 0.86s ==============================
```

## Configuration

All Viral-specific settings are in `.env`. See [`.env.example`](.env.example) for the full list:

| Key | Default | Description |
|-----|---------|-------------|
| `VIRAL_DEFAULT_POPULATION_SIZE` | 10000 | Number of agents |
| `VIRAL_DEFAULT_SUBCULTURE` | default | Population preset |
| `VIRAL_LLM_ENRICHMENT_PERCENT` | 1 | % of agents with LLM personas |
| `VIRAL_FEED_RECENCY_WEIGHT` | 0.30 | Feed ranking: recency |
| `VIRAL_FEED_POPULARITY_WEIGHT` | 0.25 | Feed ranking: popularity |
| `VIRAL_FEED_RELEVANCE_WEIGHT` | 0.25 | Feed ranking: relevance |
| `VIRAL_FEED_ECHO_WEIGHT` | 0.20 | Feed ranking: echo chamber |
| `VIRAL_FEED_NOISE` | 0.10 | Feed randomness (0–0.5) |
| `VIRAL_DASHBOARD_POLL_MS` | 3000 | Dashboard refresh rate (ms) |

## Project Structure

```
Viral/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── viral.py              # Dashboard API endpoints
│   │   ├── services/
│   │   │   ├── population_generator.py  # 10K agent batch generation
│   │   │   ├── cascade_tracker.py       # R₀, cascade trees, sentiment
│   │   │   ├── feed_algorithm.py        # 4-weight feed ranking
│   │   │   ├── mutation_engine.py       # Quote-tweet narrative mutation
│   │   │   └── sentiment_analyzer.py    # Bilingual lexicon analysis
│   │   ├── data/
│   │   │   └── subcultures.json         # Population presets
│   │   └── config.py                    # All configuration
│   └── tests/                           # 71 tests
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── ViralDashboard.vue       # D3.js dashboard UI
│   │   ├── views/
│   │   │   └── ViralDashboardView.vue   # Dashboard view + polling
│   │   └── api/
│   │       └── viral.js                 # API module
│   └── package.json
├── .env.example
└── package.json
```

## Acknowledgments

Viral's simulation engine is powered by **[OASIS](https://github.com/camel-ai/oasis)** (Open Agent Social Interaction Simulations) from the CAMEL-AI team.

## License

AGPL-3.0
