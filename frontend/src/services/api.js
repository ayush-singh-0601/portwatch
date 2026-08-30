/* ═══════════════════════════════════════════════════════════════
   API Service — Axios instance + endpoint functions
   Falls back to mock data when backend is unavailable.
   ═══════════════════════════════════════════════════════════════ */
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request interceptor ────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    // Could add auth token here in future
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response interceptor ───────────────────────────────────────
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred'

    console.error('[API Error]', {
      url: error.config?.url,
      status: error.response?.status,
      message,
    })

    return Promise.reject({ message, status: error.response?.status })
  }
)

// ── API Functions ──────────────────────────────────────────────

/** Fetch all vessels with optional query params */
export async function getVessels(params = {}) {
  return api.get('/vessels', { params })
}

/** Fetch a single vessel by IMO */
export async function getVessel(imo) {
  return api.get(`/vessels/${imo}`)
}

/** Search vessels by name */
export async function searchVessels(query) {
  return api.get('/vessels', { params: { name: query } })
}

/** Fetch AIS positions for a vessel */
export async function getPositions(imo, params = {}) {
  return api.get(`/vessels/${imo}/positions`, { params })
}

/** Fetch ownership graph for a vessel */
export async function getOwnership(imo) {
  return api.get(`/vessels/${imo}/ownership`)
}

/** Fetch sanctions screening results */
export async function getSanctions(imo) {
  return api.get(`/vessels/${imo}/sanctions`)
}

/** Fetch risk score breakdown */
export async function getRiskScore(imo) {
  return api.get(`/vessels/${imo}/risk`)
}

/** Recalculate risk score breakdown */
export async function calculateRisk(imo) {
  return api.post(`/vessels/${imo}/risk/calculate`)
}

/** Screen vessel against sanctions lists */
export async function screenSanctions(imo) {
  return api.post(`/vessels/${imo}/screen`)
}

/** Generate investigation report */
export async function generateReport(imo, format = 'pdf', sections = null) {
  const body = { format }
  if (sections) body.sections = sections
  return api.post(`/vessels/${imo}/report`, body)
}

export default api
