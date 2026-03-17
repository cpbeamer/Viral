/**
 * Viral Dashboard API module
 *
 * Provides methods for interacting with the Viral Wind Tunnel backend:
 * - Fetching cascade data (R0, sentiment, engagement metrics)
 * - Injecting seed posts into running simulations
 * - Applying population tuning and scenario presets
 * - Listing available subculture configurations
 */

import service from './index'

/**
 * Fetch current cascade data for the dashboard.
 * @param {string} simulationId
 * @returns {Promise<Object>} Cascade data with global_r0, cascades, round_metrics
 */
export const getCascadeData = (simulationId) => {
  return service({
    url: `/api/viral/cascades/${simulationId}`,
    method: 'get',
  })
}

/**
 * Inject a seed post into a running simulation.
 * @param {Object} params
 * @param {string} params.simulation_id
 * @param {string} params.content - Post text content
 * @param {number} params.reach - Author reach score (0-1)
 * @param {string} params.vibe - Author vibe profile
 * @returns {Promise<Object>} { success, post_id, message }
 */
export const injectPost = (params) => {
  return service({
    url: '/api/viral/inject',
    method: 'post',
    data: params,
  })
}

/**
 * Apply real-time parameter tuning to a simulation.
 * @param {Object} params
 * @param {string} params.simulation_id
 * @param {number} params.susceptibility_multiplier
 * @param {number} params.echo_chamber_weight
 * @param {number} params.feed_noise
 * @returns {Promise<Object>} { success, tuning }
 */
export const applyTuning = (params) => {
  return service({
    url: '/api/viral/tuning',
    method: 'post',
    data: params,
  })
}

/**
 * Apply a scenario preset to a simulation.
 * @param {Object} params
 * @param {string} params.simulation_id
 * @param {string} params.preset - Preset name (fud_storm, echo_bubble, etc.)
 * @param {Object} params.config - Preset configuration values
 * @returns {Promise<Object>} { success, preset, config }
 */
export const applyPreset = (params) => {
  return service({
    url: '/api/viral/preset',
    method: 'post',
    data: params,
  })
}

/**
 * List available subculture configurations.
 * @returns {Promise<Array>} Array of subculture configs
 */
export const getSubcultures = () => {
  return service({
    url: '/api/viral/subcultures',
    method: 'get',
  })
}
