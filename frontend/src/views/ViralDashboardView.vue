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
import { getCascadeData, injectPost, applyTuning, applyPreset } from '../api/viral'

const props = defineProps({
  simulationId: {
    type: String,
    required: true
  }
})

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
    const res = await getCascadeData(props.simulationId)
    if (res) {
      cascadeData.value = res
    }
  } catch (err) {
    console.warn('Failed to fetch cascade data:', err.message)
  }
}

const handleInjectPost = async (payload) => {
  try {
    await injectPost({
      simulation_id: props.simulationId,
      ...payload,
    })
  } catch (err) {
    console.error('Failed to inject post:', err.message)
  }
}

const handleApplyTuning = async (payload) => {
  try {
    await applyTuning({
      simulation_id: props.simulationId,
      ...payload,
    })
  } catch (err) {
    console.error('Failed to apply tuning:', err.message)
  }
}

const handleApplyPreset = async (payload) => {
  try {
    await applyPreset({
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
