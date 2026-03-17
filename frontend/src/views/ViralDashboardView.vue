<template>
  <div class="viral-view">
    <ViralDashboard
      :simulationId="simulationId"
      :cascadeData="cascadeData"
      @inject-post="handleInjectPost"
      @apply-tuning="handleApplyTuning"
      @apply-preset="handleApplyPreset"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import ViralDashboard from '../components/ViralDashboard.vue'
import axios from 'axios'

const props = defineProps({
  simulationId: {
    type: String,
    required: true
  }
})

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

const cascadeData = ref({
  global_r0: 0,
  global_sentiment: 0,
  total_cascades: 0,
  total_engagements: 0,
  cascades: [],
  round_metrics: [],
})

let pollTimer = null

const fetchCascadeData = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/viral/cascades/${props.simulationId}`)
    if (res.data) {
      cascadeData.value = res.data
    }
  } catch (err) {
    console.warn('Failed to fetch cascade data:', err.message)
  }
}

const handleInjectPost = async (payload) => {
  try {
    await axios.post(`${API_BASE}/api/viral/inject`, {
      simulation_id: props.simulationId,
      ...payload,
    })
  } catch (err) {
    console.error('Failed to inject post:', err.message)
  }
}

const handleApplyTuning = async (payload) => {
  try {
    await axios.post(`${API_BASE}/api/viral/tuning`, {
      simulation_id: props.simulationId,
      ...payload,
    })
  } catch (err) {
    console.error('Failed to apply tuning:', err.message)
  }
}

const handleApplyPreset = async (payload) => {
  try {
    await axios.post(`${API_BASE}/api/viral/preset`, {
      simulation_id: props.simulationId,
      ...payload,
    })
  } catch (err) {
    console.error('Failed to apply preset:', err.message)
  }
}

onMounted(() => {
  fetchCascadeData()
  pollTimer = setInterval(fetchCascadeData, 3000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.viral-view {
  width: 100%;
  height: 100vh;
}
</style>
