<template>
  <div class="viral-dashboard">
    <!-- Dashboard Header -->
    <header class="dash-header">
      <div class="dash-title-group">
        <h1 class="dash-title">
          <svg class="virus-icon" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="4"></circle>
            <line x1="12" y1="2" x2="12" y2="6"></line>
            <line x1="12" y1="18" x2="12" y2="22"></line>
            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
            <line x1="2" y1="12" x2="6" y2="12"></line>
            <line x1="18" y1="12" x2="22" y2="12"></line>
            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
            <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
          </svg>
          VIRAL — Wind Tunnel
        </h1>
        <span class="sim-id-badge">{{ simulationId || 'DEMO' }}</span>
      </div>
      <div class="dash-controls">
        <div class="round-display">
          <span class="round-label">ROUND</span>
          <span class="round-value mono">{{ currentRound }}</span>
        </div>
        <button class="tab-btn" :class="{ active: activeTab === 'overview' }" @click="activeTab = 'overview'">Overview</button>
        <button class="tab-btn" :class="{ active: activeTab === 'cascade' }" @click="activeTab = 'cascade'">Cascades</button>
        <button class="tab-btn" :class="{ active: activeTab === 'godmode' }" @click="activeTab = 'godmode'">God Mode</button>
      </div>
    </header>

    <!-- Overview Tab -->
    <div v-if="activeTab === 'overview'" class="dash-body">
      <!-- Top KPI Row -->
      <div class="kpi-row">
        <div class="kpi-card kpi-r0" :class="r0StatusClass">
          <div class="kpi-label">R₀ — Reproduction Number</div>
          <div class="kpi-value-row">
            <span class="kpi-big mono">{{ globalR0.toFixed(2) }}</span>
            <span class="kpi-tag" :class="r0StatusClass">{{ r0StatusLabel }}</span>
          </div>
          <div class="r0-bar-track">
            <div class="r0-bar-fill" :style="{ width: r0BarWidth + '%' }"></div>
            <div class="r0-threshold" style="left: 33.3%"><span>1.0</span></div>
          </div>
          <div class="kpi-subtitle">{{ r0Explanation }}</div>
        </div>

        <div class="kpi-card kpi-sentiment">
          <div class="kpi-label">Global Sentiment</div>
          <div class="kpi-value-row">
            <span class="kpi-big mono" :class="sentimentClass">{{ globalSentiment >= 0 ? '+' : '' }}{{ globalSentiment.toFixed(3) }}</span>
            <span class="kpi-tag" :class="sentimentClass">{{ sentimentLabel }}</span>
          </div>
          <div class="sentiment-bar-track">
            <div class="sentiment-indicator" :style="{ left: sentimentPosition + '%' }"></div>
          </div>
          <div class="kpi-subtitle">Drift: {{ sentimentDrift >= 0 ? '+' : '' }}{{ sentimentDrift.toFixed(4) }}/round</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Total Engagements</div>
          <div class="kpi-big mono">{{ totalEngagements.toLocaleString() }}</div>
          <div class="kpi-breakdown">
            <span class="breakdown-chip like">❤️ {{ engagementBreakdown.likes }}</span>
            <span class="breakdown-chip repost">🔁 {{ engagementBreakdown.reposts }}</span>
            <span class="breakdown-chip quote">💬 {{ engagementBreakdown.quotes }}</span>
            <span class="breakdown-chip reply">↩️ {{ engagementBreakdown.replies }}</span>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Active Cascades</div>
          <div class="kpi-big mono">{{ activeCascades }}</div>
          <div class="kpi-subtitle">{{ uniqueAgentsEngaged.toLocaleString() }} agents engaged</div>
          <div class="kpi-subtitle">Max depth: {{ maxCascadeDepth }}</div>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="charts-row">
        <!-- R0 Timeline -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>R₀ Over Time</h3>
            <span class="chart-badge" :class="r0StatusClass">{{ r0TrendLabel }}</span>
          </div>
          <div class="chart-body" ref="r0ChartRef"></div>
        </div>

        <!-- Sentiment Timeline -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>Sentiment Timeline</h3>
            <span class="chart-badge" :class="sentimentClass">{{ sentimentTrendLabel }}</span>
          </div>
          <div class="chart-body" ref="sentimentChartRef"></div>
        </div>
      </div>

      <!-- Engagement Heatmap -->
      <div class="chart-card full-width">
        <div class="chart-header">
          <h3>Engagement Heatmap by Round</h3>
        </div>
        <div class="chart-body heatmap-body" ref="heatmapRef"></div>
      </div>
    </div>

    <!-- Cascades Tab -->
    <div v-if="activeTab === 'cascade'" class="dash-body">
      <div class="cascade-grid">
        <!-- Top Cascades List -->
        <div class="cascade-list-panel">
          <h3 class="panel-title">Top Cascades</h3>
          <div
            v-for="(cascade, idx) in topCascades"
            :key="cascade.post_id"
            class="cascade-item"
            :class="{ selected: selectedCascade?.post_id === cascade.post_id }"
            @click="selectedCascade = cascade"
          >
            <div class="cascade-rank">#{{ idx + 1 }}</div>
            <div class="cascade-info">
              <div class="cascade-content">{{ truncate(cascade.original_content, 80) }}</div>
              <div class="cascade-stats">
                <span class="cascade-stat">R₀ <strong class="mono">{{ cascade.r0.toFixed(1) }}</strong></span>
                <span class="cascade-stat">Depth <strong class="mono">{{ cascade.max_depth }}</strong></span>
                <span class="cascade-stat">Eng. <strong class="mono">{{ cascade.total_engagements }}</strong></span>
              </div>
            </div>
          </div>
          <div v-if="topCascades.length === 0" class="empty-state">No cascades yet</div>
        </div>

        <!-- Cascade Detail -->
        <div class="cascade-detail-panel">
          <template v-if="selectedCascade">
            <div class="detail-header">
              <h3>Cascade Tree</h3>
              <span class="detail-badge mono">{{ selectedCascade.post_id }}</span>
            </div>
            <div class="cascade-tree-viz" ref="cascadeTreeRef"></div>

            <!-- Mutations -->
            <div v-if="selectedCascade.mutations?.length" class="mutations-panel">
              <h4 class="panel-subtitle">Narrative Mutations ({{ selectedCascade.mutations.length }})</h4>
              <div
                v-for="(mutation, mIdx) in selectedCascade.mutations.slice(0, 10)"
                :key="mIdx"
                class="mutation-item"
              >
                <div class="mutation-depth">Depth {{ mutation.depth }}</div>
                <div class="mutation-content">"{{ truncate(mutation.content, 120) }}"</div>
              </div>
            </div>
          </template>
          <div v-else class="empty-state">Select a cascade to view its tree</div>
        </div>
      </div>
    </div>

    <!-- God Mode Tab -->
    <div v-if="activeTab === 'godmode'" class="dash-body">
      <div class="godmode-grid">
        <!-- Inject Post -->
        <div class="godmode-card">
          <h3 class="panel-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>
            Inject Seed Post
          </h3>
          <div class="godmode-form">
            <textarea
              v-model="injectContent"
              class="godmode-textarea"
              placeholder="Type a post to inject into the simulation..."
              rows="3"
            ></textarea>
            <div class="inject-options">
              <label class="option-label">
                Author Reach:
                <input type="range" v-model.number="injectReach" min="0" max="1" step="0.01" class="range-input">
                <span class="mono">{{ injectReach.toFixed(2) }}</span>
              </label>
              <label class="option-label">
                Author Vibe:
                <select v-model="injectVibe" class="select-input">
                  <option v-for="v in vibeOptions" :key="v" :value="v">{{ v }}</option>
                </select>
              </label>
            </div>
            <button class="godmode-btn inject" @click="handleInjectPost" :disabled="!injectContent.trim()">
              ⚡ Inject Post
            </button>
          </div>
        </div>

        <!-- Modify Susceptibility -->
        <div class="godmode-card">
          <h3 class="panel-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
            Population Tuning
          </h3>
          <div class="godmode-form">
            <label class="option-label">
              Global Susceptibility Multiplier:
              <input type="range" v-model.number="susceptibilityMultiplier" min="0.1" max="3.0" step="0.1" class="range-input">
              <span class="mono">{{ susceptibilityMultiplier.toFixed(1) }}×</span>
            </label>
            <label class="option-label">
              Echo Chamber Strength:
              <input type="range" v-model.number="echoChamberWeight" min="0" max="1" step="0.05" class="range-input">
              <span class="mono">{{ echoChamberWeight.toFixed(2) }}</span>
            </label>
            <label class="option-label">
              Feed Noise:
              <input type="range" v-model.number="feedNoise" min="0" max="0.5" step="0.01" class="range-input">
              <span class="mono">{{ feedNoise.toFixed(2) }}</span>
            </label>
            <button class="godmode-btn apply" @click="handleApplyTuning">
              🎛️ Apply Tuning
            </button>
          </div>
        </div>

        <!-- Scenario Presets -->
        <div class="godmode-card">
          <h3 class="panel-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
            Scenario Presets
          </h3>
          <div class="preset-grid">
            <button class="preset-btn" @click="applyPreset('fud_storm')">
              <span class="preset-icon">🌪️</span>
              <span class="preset-name">FUD Storm</span>
              <span class="preset-desc">High susceptibility, aggressive vibes</span>
            </button>
            <button class="preset-btn" @click="applyPreset('echo_bubble')">
              <span class="preset-icon">🫧</span>
              <span class="preset-name">Echo Bubble</span>
              <span class="preset-desc">Max echo chamber, low noise</span>
            </button>
            <button class="preset-btn" @click="applyPreset('fact_check')">
              <span class="preset-icon">🔍</span>
              <span class="preset-name">Fact-Check Wave</span>
              <span class="preset-desc">High skepticism, low susceptibility</span>
            </button>
            <button class="preset-btn" @click="applyPreset('viral_bomb')">
              <span class="preset-icon">💣</span>
              <span class="preset-name">Viral Bomb</span>
              <span class="preset-desc">Max reach, max amplification</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  simulationId: String,
  // Cascade data from the backend
  cascadeData: {
    type: Object,
    default: () => ({
      global_r0: 0,
      global_sentiment: 0,
      total_cascades: 0,
      total_engagements: 0,
      cascades: [],
      round_metrics: [],
    })
  }
})

const emit = defineEmits([
  'inject-post',
  'apply-tuning',
  'apply-preset',
])

// --- State ---
const activeTab = ref('overview')
const selectedCascade = ref(null)

// God Mode state
const injectContent = ref('')
const injectReach = ref(0.8)
const injectVibe = ref('Opportunistic')
const susceptibilityMultiplier = ref(1.0)
const echoChamberWeight = ref(0.20)
const feedNoise = ref(0.10)

const vibeOptions = ['Skeptical', 'Aggressive', 'Helpful', 'Opportunistic', 'Neutral', 'Contrarian', 'Amplifier']

// Chart refs
const r0ChartRef = ref(null)
const sentimentChartRef = ref(null)
const heatmapRef = ref(null)
const cascadeTreeRef = ref(null)

// --- Computed ---
const currentRound = computed(() => {
  const metrics = props.cascadeData?.round_metrics || []
  return metrics.length > 0 ? metrics[metrics.length - 1].round : 0
})

const globalR0 = computed(() => props.cascadeData?.global_r0 || 0)
const globalSentiment = computed(() => props.cascadeData?.global_sentiment || 0)
const totalEngagements = computed(() => props.cascadeData?.total_engagements || 0)
const activeCascades = computed(() => props.cascadeData?.total_cascades || 0)

const uniqueAgentsEngaged = computed(() => {
  const metrics = props.cascadeData?.round_metrics || []
  return metrics.length > 0 ? metrics[metrics.length - 1].total_unique_agents || 0 : 0
})

const maxCascadeDepth = computed(() => {
  const cascades = props.cascadeData?.cascades || []
  return cascades.reduce((max, c) => Math.max(max, c.max_depth || 0), 0)
})

const topCascades = computed(() => props.cascadeData?.cascades || [])

const sentimentDrift = computed(() => {
  const metrics = props.cascadeData?.round_metrics || []
  if (metrics.length < 2) return 0
  const recent = metrics.slice(-5)
  const first = recent[0]?.global_sentiment || 0
  const last = recent[recent.length - 1]?.global_sentiment || 0
  return (last - first) / recent.length
})

const engagementBreakdown = computed(() => {
  const cascades = props.cascadeData?.cascades || []
  return {
    likes: cascades.reduce((s, c) => s + (c.like_count || 0), 0),
    reposts: cascades.reduce((s, c) => s + (c.repost_count || 0), 0),
    quotes: cascades.reduce((s, c) => s + (c.quote_count || 0), 0),
    replies: cascades.reduce((s, c) => s + (c.reply_count || 0), 0),
  }
})

// R0 status
const r0StatusClass = computed(() => {
  if (globalR0.value >= 2.0) return 'status-critical'
  if (globalR0.value >= 1.0) return 'status-warning'
  return 'status-healthy'
})

const r0StatusLabel = computed(() => {
  if (globalR0.value >= 2.0) return 'VIRAL'
  if (globalR0.value >= 1.0) return 'SPREADING'
  return 'CONTAINED'
})

const r0Explanation = computed(() => {
  if (globalR0.value >= 2.0) return 'Cascade is accelerating exponentially'
  if (globalR0.value >= 1.0) return 'Each share generates >1 secondary share'
  return 'Cascade is decaying — not reaching critical mass'
})

const r0BarWidth = computed(() => Math.min(100, (globalR0.value / 3) * 100))

const r0TrendLabel = computed(() => {
  const metrics = props.cascadeData?.round_metrics || []
  if (metrics.length < 2) return '—'
  const prev = metrics[metrics.length - 2]?.global_r0 || 0
  const curr = metrics[metrics.length - 1]?.global_r0 || 0
  if (curr > prev + 0.05) return '↑ Growing'
  if (curr < prev - 0.05) return '↓ Declining'
  return '→ Stable'
})

// Sentiment status
const sentimentClass = computed(() => {
  if (globalSentiment.value > 0.2) return 'status-positive'
  if (globalSentiment.value < -0.2) return 'status-negative'
  return 'status-neutral'
})

const sentimentLabel = computed(() => {
  if (globalSentiment.value > 0.2) return 'POSITIVE'
  if (globalSentiment.value < -0.2) return 'NEGATIVE'
  return 'NEUTRAL'
})

const sentimentPosition = computed(() => (globalSentiment.value + 1) / 2 * 100)

const sentimentTrendLabel = computed(() => {
  if (sentimentDrift.value > 0.01) return '↑ Improving'
  if (sentimentDrift.value < -0.01) return '↓ Souring'
  return '→ Stable'
})

// --- Methods ---
const truncate = (text, max = 100) => {
  if (!text) return ''
  return text.length > max ? text.substring(0, max) + '...' : text
}

const handleInjectPost = () => {
  if (!injectContent.value.trim()) return
  emit('inject-post', {
    content: injectContent.value.trim(),
    reach: injectReach.value,
    vibe: injectVibe.value,
  })
  injectContent.value = ''
}

const handleApplyTuning = () => {
  emit('apply-tuning', {
    susceptibility_multiplier: susceptibilityMultiplier.value,
    echo_chamber_weight: echoChamberWeight.value,
    feed_noise: feedNoise.value,
  })
}

const applyPreset = (preset) => {
  const presets = {
    fud_storm: { susceptibility_multiplier: 2.5, echo_chamber_weight: 0.40, feed_noise: 0.05 },
    echo_bubble: { susceptibility_multiplier: 1.5, echo_chamber_weight: 0.80, feed_noise: 0.02 },
    fact_check: { susceptibility_multiplier: 0.3, echo_chamber_weight: 0.10, feed_noise: 0.15 },
    viral_bomb: { susceptibility_multiplier: 3.0, echo_chamber_weight: 0.50, feed_noise: 0.08 },
  }
  const config = presets[preset]
  if (config) {
    susceptibilityMultiplier.value = config.susceptibility_multiplier
    echoChamberWeight.value = config.echo_chamber_weight
    feedNoise.value = config.feed_noise
    emit('apply-preset', { preset, config })
  }
}

// --- D3 Chart Rendering ---
const drawR0Chart = () => {
  if (!r0ChartRef.value) return
  const metrics = props.cascadeData?.round_metrics || []
  if (metrics.length === 0) return

  const container = r0ChartRef.value
  d3.select(container).selectAll('*').remove()

  const margin = { top: 16, right: 20, bottom: 28, left: 40 }
  const width = container.clientWidth - margin.left - margin.right
  const height = container.clientHeight - margin.top - margin.bottom

  if (width <= 0 || height <= 0) return

  const svg = d3.select(container).append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  const x = d3.scaleLinear()
    .domain(d3.extent(metrics, d => d.round))
    .range([0, width])

  const y = d3.scaleLinear()
    .domain([0, Math.max(3, d3.max(metrics, d => d.global_r0) * 1.2)])
    .range([height, 0])

  // Grid lines
  svg.append('g').attr('class', 'grid')
    .call(d3.axisLeft(y).ticks(5).tickSize(-width).tickFormat(''))
    .selectAll('line').attr('stroke', '#f0f0f0')

  // R0 = 1 threshold line
  svg.append('line')
    .attr('x1', 0).attr('x2', width)
    .attr('y1', y(1)).attr('y2', y(1))
    .attr('stroke', '#f59e0b').attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '6,4')

  svg.append('text')
    .attr('x', width - 4).attr('y', y(1) - 6)
    .attr('text-anchor', 'end').attr('fill', '#f59e0b')
    .attr('font-size', '10px').attr('font-weight', 600)
    .text('R₀ = 1.0')

  // Area fill under the line
  const area = d3.area()
    .x(d => x(d.round))
    .y0(height)
    .y1(d => y(d.global_r0))
    .curve(d3.curveMonotoneX)

  const gradient = svg.append('defs').append('linearGradient')
    .attr('id', 'r0-gradient').attr('x1', '0').attr('y1', '0').attr('x2', '0').attr('y2', '1')
  gradient.append('stop').attr('offset', '0%').attr('stop-color', '#ef4444').attr('stop-opacity', 0.3)
  gradient.append('stop').attr('offset', '100%').attr('stop-color', '#ef4444').attr('stop-opacity', 0.02)

  svg.append('path').datum(metrics)
    .attr('d', area).attr('fill', 'url(#r0-gradient)')

  // Line
  const line = d3.line()
    .x(d => x(d.round))
    .y(d => y(d.global_r0))
    .curve(d3.curveMonotoneX)

  svg.append('path').datum(metrics)
    .attr('d', line).attr('fill', 'none')
    .attr('stroke', '#ef4444').attr('stroke-width', 2.5)

  // Dots
  svg.selectAll('.dot').data(metrics).enter().append('circle')
    .attr('cx', d => x(d.round)).attr('cy', d => y(d.global_r0))
    .attr('r', 3).attr('fill', '#ef4444')

  // Axes
  svg.append('g').attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x).ticks(Math.min(metrics.length, 10)).tickFormat(d => `R${d}`))
    .selectAll('text').attr('fill', '#888').attr('font-size', '10px')
  svg.append('g')
    .call(d3.axisLeft(y).ticks(5))
    .selectAll('text').attr('fill', '#888').attr('font-size', '10px')
}

const drawSentimentChart = () => {
  if (!sentimentChartRef.value) return
  const metrics = props.cascadeData?.round_metrics || []
  if (metrics.length === 0) return

  const container = sentimentChartRef.value
  d3.select(container).selectAll('*').remove()

  const margin = { top: 16, right: 20, bottom: 28, left: 40 }
  const width = container.clientWidth - margin.left - margin.right
  const height = container.clientHeight - margin.top - margin.bottom

  if (width <= 0 || height <= 0) return

  const svg = d3.select(container).append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  const x = d3.scaleLinear()
    .domain(d3.extent(metrics, d => d.round))
    .range([0, width])

  const y = d3.scaleLinear()
    .domain([-1, 1])
    .range([height, 0])

  // Zero line
  svg.append('line')
    .attr('x1', 0).attr('x2', width)
    .attr('y1', y(0)).attr('y2', y(0))
    .attr('stroke', '#ddd').attr('stroke-width', 1)

  // Positive area
  const areaPos = d3.area()
    .x(d => x(d.round))
    .y0(y(0))
    .y1(d => y(Math.max(0, d.global_sentiment)))
    .curve(d3.curveMonotoneX)

  svg.append('path').datum(metrics)
    .attr('d', areaPos)
    .attr('fill', '#10b981').attr('fill-opacity', 0.15)

  // Negative area
  const areaNeg = d3.area()
    .x(d => x(d.round))
    .y0(y(0))
    .y1(d => y(Math.min(0, d.global_sentiment)))
    .curve(d3.curveMonotoneX)

  svg.append('path').datum(metrics)
    .attr('d', areaNeg)
    .attr('fill', '#ef4444').attr('fill-opacity', 0.15)

  // Line
  const line = d3.line()
    .x(d => x(d.round))
    .y(d => y(d.global_sentiment))
    .curve(d3.curveMonotoneX)

  svg.append('path').datum(metrics)
    .attr('d', line).attr('fill', 'none')
    .attr('stroke', '#6366f1').attr('stroke-width', 2.5)

  // Dots
  svg.selectAll('.dot').data(metrics).enter().append('circle')
    .attr('cx', d => x(d.round)).attr('cy', d => y(d.global_sentiment))
    .attr('r', 3)
    .attr('fill', d => d.global_sentiment >= 0 ? '#10b981' : '#ef4444')

  // Axes
  svg.append('g').attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(x).ticks(Math.min(metrics.length, 10)).tickFormat(d => `R${d}`))
    .selectAll('text').attr('fill', '#888').attr('font-size', '10px')
  svg.append('g')
    .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format('+.1f')))
    .selectAll('text').attr('fill', '#888').attr('font-size', '10px')
}

const drawHeatmap = () => {
  if (!heatmapRef.value) return
  const metrics = props.cascadeData?.round_metrics || []
  if (metrics.length === 0) return

  const container = heatmapRef.value
  d3.select(container).selectAll('*').remove()

  const margin = { top: 16, right: 20, bottom: 28, left: 60 }
  const width = container.clientWidth - margin.left - margin.right
  const height = container.clientHeight - margin.top - margin.bottom

  if (width <= 0 || height <= 0) return

  const svg = d3.select(container).append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  const categories = ['Engagements', 'R₀', 'Sentiment']
  const cellWidth = width / metrics.length
  const cellHeight = height / categories.length

  const engMax = d3.max(metrics, d => d.total_engagements) || 1

  const colorScales = {
    'Engagements': d3.scaleSequential(d3.interpolateYlOrRd).domain([0, engMax]),
    'R₀': d3.scaleSequential(d3.interpolateRdYlGn).domain([3, 0]),
    'Sentiment': d3.scaleDiverging(d3.interpolateRdBu).domain([-1, 0, 1]),
  }

  categories.forEach((cat, catIdx) => {
    metrics.forEach((m, roundIdx) => {
      let value = 0
      if (cat === 'Engagements') value = m.total_engagements || 0
      else if (cat === 'R₀') value = m.global_r0 || 0
      else if (cat === 'Sentiment') value = m.global_sentiment || 0

      svg.append('rect')
        .attr('x', roundIdx * cellWidth)
        .attr('y', catIdx * cellHeight)
        .attr('width', Math.max(1, cellWidth - 1))
        .attr('height', Math.max(1, cellHeight - 2))
        .attr('rx', 2)
        .attr('fill', colorScales[cat](value))
        .attr('opacity', 0.85)

      // Value label for small datasets
      if (metrics.length <= 20) {
        let label = ''
        if (cat === 'Engagements') label = value.toString()
        else if (cat === 'R₀') label = value.toFixed(1)
        else label = value.toFixed(2)

        svg.append('text')
          .attr('x', roundIdx * cellWidth + cellWidth / 2)
          .attr('y', catIdx * cellHeight + cellHeight / 2 + 4)
          .attr('text-anchor', 'middle')
          .attr('fill', '#333').attr('font-size', '10px').attr('font-weight', 600)
          .text(label)
      }
    })
  })

  // Y-axis labels
  categories.forEach((cat, catIdx) => {
    svg.append('text')
      .attr('x', -8).attr('y', catIdx * cellHeight + cellHeight / 2 + 4)
      .attr('text-anchor', 'end').attr('fill', '#666')
      .attr('font-size', '11px').attr('font-weight', 500)
      .text(cat)
  })

  // X-axis
  if (metrics.length <= 30) {
    metrics.forEach((m, i) => {
      svg.append('text')
        .attr('x', i * cellWidth + cellWidth / 2)
        .attr('y', height + 16)
        .attr('text-anchor', 'middle').attr('fill', '#888')
        .attr('font-size', '10px')
        .text(`R${m.round}`)
    })
  }
}

const drawCascadeTree = () => {
  if (!cascadeTreeRef.value || !selectedCascade.value) return

  const container = cascadeTreeRef.value
  d3.select(container).selectAll('*').remove()

  const cascade = selectedCascade.value
  const edges = cascade.cascade_breadth || {}

  // Build simple depth visualization as horizontal bar chart
  const depths = Object.entries(edges).map(([depth, count]) => ({
    depth: parseInt(depth),
    count,
  })).sort((a, b) => a.depth - b.depth)

  if (depths.length === 0) return

  const margin = { top: 12, right: 20, bottom: 28, left: 50 }
  const width = container.clientWidth - margin.left - margin.right
  const height = Math.max(120, depths.length * 32)

  const svg = d3.select(container).append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  const x = d3.scaleLinear()
    .domain([0, d3.max(depths, d => d.count)])
    .range([0, width])

  const y = d3.scaleBand()
    .domain(depths.map(d => `Depth ${d.depth}`))
    .range([0, height])
    .padding(0.3)

  // Bars
  svg.selectAll('.bar').data(depths).enter().append('rect')
    .attr('x', 0)
    .attr('y', d => y(`Depth ${d.depth}`))
    .attr('width', d => x(d.count))
    .attr('height', y.bandwidth())
    .attr('rx', 3)
    .attr('fill', (d, i) => d3.interpolateViridis(i / Math.max(depths.length - 1, 1)))

  // Labels
  svg.selectAll('.label').data(depths).enter().append('text')
    .attr('x', d => x(d.count) + 6)
    .attr('y', d => y(`Depth ${d.depth}`) + y.bandwidth() / 2 + 4)
    .attr('fill', '#333').attr('font-size', '12px').attr('font-weight', 600)
    .text(d => `${d.count} agents`)

  // Y-axis
  svg.append('g')
    .call(d3.axisLeft(y))
    .selectAll('text').attr('fill', '#555').attr('font-size', '11px')
}

// --- Watchers ---
watch(() => props.cascadeData, () => {
  nextTick(() => {
    if (activeTab.value === 'overview') {
      drawR0Chart()
      drawSentimentChart()
      drawHeatmap()
    } else if (activeTab.value === 'cascade' && selectedCascade.value) {
      drawCascadeTree()
    }
  })
}, { deep: true })

watch(activeTab, (tab) => {
  nextTick(() => {
    if (tab === 'overview') {
      drawR0Chart()
      drawSentimentChart()
      drawHeatmap()
    }
  })
})

watch(selectedCascade, () => {
  nextTick(() => drawCascadeTree())
})

onMounted(() => {
  nextTick(() => {
    drawR0Chart()
    drawSentimentChart()
    drawHeatmap()
  })
})
</script>

<style scoped>
/* ============================================
   VIRAL DASHBOARD — Premium Dark Theme
   ============================================ */
.viral-dashboard {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0a0a0f;
  color: #e4e4e7;
  font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif;
  overflow: hidden;
}

/* --- Header --- */
.dash-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 24px;
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.dash-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dash-title {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: 0.03em;
  margin: 0;
}

.virus-icon {
  color: #f43f5e;
  animation: pulse-icon 2s ease-in-out infinite;
}

@keyframes pulse-icon {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.sim-id-badge {
  font-size: 10px;
  font-weight: 600;
  color: #888;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  padding: 2px 8px;
  border-radius: 3px;
  font-family: 'Space Mono', monospace;
}

.dash-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.round-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2px 14px;
  margin-right: 12px;
}

.round-label {
  font-size: 9px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.round-value {
  font-size: 18px;
  font-weight: 700;
  color: #f43f5e;
}

.tab-btn {
  background: transparent;
  border: 1px solid rgba(255,255,255,0.08);
  color: #888;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 14px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.tab-btn:hover {
  color: #e4e4e7;
  border-color: rgba(255,255,255,0.15);
}

.tab-btn.active {
  color: #fff;
  background: rgba(244,63,94,0.15);
  border-color: #f43f5e;
}

/* --- Body --- */
.dash-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.dash-body::-webkit-scrollbar {
  width: 4px;
}
.dash-body::-webkit-scrollbar-track {
  background: transparent;
}
.dash-body::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
}

/* --- KPI Row --- */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.kpi-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 16px 18px;
  transition: border-color 0.3s;
}

.kpi-card:hover {
  border-color: rgba(255,255,255,0.12);
}

.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}

.kpi-value-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.kpi-big {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.kpi-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 3px;
  letter-spacing: 0.05em;
}

.kpi-subtitle {
  font-size: 11px;
  color: #666;
  margin-top: 4px;
}

.kpi-breakdown {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.breakdown-chip {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(255,255,255,0.04);
}

/* Status colors */
.status-critical { color: #f43f5e; }
.status-critical.kpi-tag { background: rgba(244,63,94,0.15); }
.status-warning { color: #f59e0b; }
.status-warning.kpi-tag { background: rgba(245,158,11,0.15); }
.status-healthy { color: #10b981; }
.status-healthy.kpi-tag { background: rgba(16,185,129,0.15); }
.status-positive { color: #10b981; }
.status-positive.kpi-tag { background: rgba(16,185,129,0.15); }
.status-negative { color: #ef4444; }
.status-negative.kpi-tag { background: rgba(239,68,68,0.15); }
.status-neutral { color: #a78bfa; }
.status-neutral.kpi-tag { background: rgba(167,139,250,0.15); }

/* R0 bar */
.r0-bar-track {
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 3px;
  position: relative;
  margin-bottom: 4px;
}

.r0-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #10b981, #f59e0b, #f43f5e);
  transition: width 0.5s ease;
}

.r0-threshold {
  position: absolute;
  top: -12px;
  transform: translateX(-50%);
}

.r0-threshold span {
  font-size: 8px;
  color: #f59e0b;
  font-weight: 600;
}

/* Sentiment bar */
.sentiment-bar-track {
  width: 100%;
  height: 6px;
  background: linear-gradient(90deg, #ef4444, #a78bfa, #10b981);
  border-radius: 3px;
  position: relative;
  opacity: 0.3;
}

.sentiment-indicator {
  position: absolute;
  top: -3px;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  transform: translateX(-50%);
  box-shadow: 0 0 6px rgba(255,255,255,0.4);
  transition: left 0.5s ease;
}

/* --- Charts --- */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.chart-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  overflow: hidden;
}

.chart-card.full-width {
  margin-bottom: 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}

.chart-header h3 {
  font-size: 13px;
  font-weight: 600;
  color: #ccc;
  margin: 0;
}

.chart-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 3px;
  background: rgba(255,255,255,0.05);
}

.chart-body {
  height: 200px;
  padding: 4px;
}

.heatmap-body {
  height: 120px;
}

/* D3 chart global overrides inside dashboard */
.chart-body :deep(.domain) { stroke: rgba(255,255,255,0.1); }
.chart-body :deep(.tick line) { stroke: rgba(255,255,255,0.05); }

/* --- Cascades Tab --- */
.cascade-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  height: calc(100vh - 140px);
}

.cascade-list-panel {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 16px;
  overflow-y: auto;
}

.cascade-detail-panel {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 16px;
  overflow-y: auto;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #ccc;
  margin: 0 0 14px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-subtitle {
  font-size: 12px;
  font-weight: 600;
  color: #aaa;
  margin: 14px 0 8px 0;
}

.cascade-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 4px;
}

.cascade-item:hover {
  background: rgba(255,255,255,0.05);
}

.cascade-item.selected {
  background: rgba(244,63,94,0.1);
  border-left: 3px solid #f43f5e;
}

.cascade-rank {
  font-size: 12px;
  font-weight: 700;
  color: #f43f5e;
  min-width: 28px;
}

.cascade-info {
  flex: 1;
  min-width: 0;
}

.cascade-content {
  font-size: 12px;
  color: #ccc;
  margin-bottom: 6px;
  word-break: break-word;
}

.cascade-stats {
  display: flex;
  gap: 12px;
}

.cascade-stat {
  font-size: 10px;
  color: #888;
}

.cascade-stat strong {
  color: #e4e4e7;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.detail-badge {
  font-size: 10px;
  color: #888;
  background: rgba(255,255,255,0.05);
  padding: 2px 8px;
  border-radius: 3px;
}

.cascade-tree-viz {
  min-height: 200px;
}

.mutations-panel {
  margin-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 12px;
}

.mutation-item {
  padding: 8px 10px;
  margin-bottom: 6px;
  background: rgba(255,255,255,0.03);
  border-radius: 4px;
  border-left: 2px solid #a78bfa;
}

.mutation-depth {
  font-size: 9px;
  font-weight: 700;
  color: #a78bfa;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.mutation-content {
  font-size: 12px;
  color: #ccc;
  font-style: italic;
}

/* --- God Mode Tab --- */
.godmode-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.godmode-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 18px;
}

.godmode-card .panel-title svg {
  color: #f59e0b;
}

.godmode-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.godmode-textarea {
  width: 100%;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  padding: 10px 12px;
  color: #e4e4e7;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box;
}

.godmode-textarea:focus {
  outline: none;
  border-color: #f43f5e;
}

.godmode-textarea::placeholder {
  color: #555;
}

.inject-options {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.option-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #aaa;
}

.range-input {
  width: 100px;
  accent-color: #f43f5e;
}

.select-input {
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.08);
  color: #e4e4e7;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: inherit;
}

.godmode-btn {
  padding: 10px 18px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.godmode-btn.inject {
  background: linear-gradient(135deg, #f43f5e, #e11d48);
  color: #fff;
}

.godmode-btn.inject:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(244,63,94,0.3);
}

.godmode-btn.inject:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.godmode-btn.apply {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  color: #fff;
}

.godmode-btn.apply:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99,102,241,0.3);
}

/* Preset buttons */
.preset-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 12px;
  background: rgba(0,0,0,0.2);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}

.preset-btn:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.12);
  transform: translateY(-1px);
}

.preset-icon {
  font-size: 24px;
}

.preset-name {
  font-size: 12px;
  font-weight: 700;
  color: #e4e4e7;
}

.preset-desc {
  font-size: 10px;
  color: #888;
}

/* --- Shared Utils --- */
.mono {
  font-family: 'Space Mono', 'SF Mono', monospace;
}

.empty-state {
  text-align: center;
  color: #555;
  font-size: 13px;
  padding: 40px 20px;
}

/* --- Responsive --- */
@media (max-width: 1200px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
  .godmode-grid { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .kpi-row { grid-template-columns: 1fr; }
  .cascade-grid { grid-template-columns: 1fr; }
}

/* --- Light mode support --- */
@media (prefers-color-scheme: light) {
  .viral-dashboard {
    background: #f8f9fa;
    color: #1a1a2e;
  }
  .dash-header {
    background: linear-gradient(135deg, #fff, #f1f5f9);
    border-bottom-color: #e2e8f0;
  }
  .dash-title { color: #1a1a2e; }
  .kpi-card, .chart-card, .cascade-list-panel, .cascade-detail-panel, .godmode-card {
    background: #fff;
    border-color: #e2e8f0;
  }
  .kpi-big { color: #1a1a2e; }
  .kpi-label { color: #64748b; }
  .tab-btn { color: #64748b; border-color: #e2e8f0; }
  .tab-btn.active { color: #1a1a2e; background: rgba(244,63,94,0.08); }
  .godmode-textarea { background: #f8f9fa; border-color: #e2e8f0; color: #1a1a2e; }
  .select-input { background: #f8f9fa; border-color: #e2e8f0; color: #1a1a2e; }
  .cascade-content { color: #374151; }
  .mutation-content { color: #4b5563; }
}
</style>
