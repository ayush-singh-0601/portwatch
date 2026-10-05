/* ═══════════════════════════════════════════════════════════════
   API Service — Axios instance + endpoint functions
   Falls back to mock data when backend is unavailable.
   ═══════════════════════════════════════════════════════════════ */
import axios from 'axios'

const api = axios.create({
  baseURL: (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || '/api',
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

    const err = new Error(message)
    err.status = error.response?.status
    err.data = error.response?.data
    err.config = error.config

    return Promise.reject(err)
  }
)

// ── Helper ────────────────────────────────────────────────────
function cleanImo(imo) {
  if (!imo) return imo
  const digits = String(imo).replace(/\D/g, '')
  return digits || imo
}

// ── API Functions ──────────────────────────────────────────────

/** Fetch all vessels with optional query params */
export async function getVessels(params = {}) {
  return api.get('/vessels', { params })
}

/** Fetch enriched vessels list with embedded telemetry, risk, and sanctions */
export async function getEnrichedVessels(params = {}) {
  return api.get('/vessels/enriched', { params })
}

/** Fetch a single vessel by IMO */
export async function getVessel(imo) {
  return api.get(`/vessels/${cleanImo(imo)}`)
}

/** Fetch a single vessel by MMSI when IMO is unknown */
export async function getVesselByMmsi(mmsi) {
  if (!mmsi) return null
  const cleanMmsi = String(mmsi).replace(/\D/g, '')
  return api.get(`/vessels/mmsi/${cleanMmsi}`)
}

/** Search vessels by name */
export async function searchVessels(query) {
  return api.get('/vessels', { params: { name: query } })
}

/** Fetch AIS positions for a vessel */
export async function getPositions(imo, params = {}) {
  return api.get(`/vessels/${cleanImo(imo)}/positions`, { params })
}

/** Fetch ownership graph for a vessel */
export async function getOwnership(imo) {
  return api.get(`/vessels/${cleanImo(imo)}/ownership`)
}

/** Fetch sanctions screening results */
export async function getSanctions(imo) {
  return api.get(`/vessels/${cleanImo(imo)}/sanctions`)
}

/** Fetch risk score breakdown */
export async function getRiskScore(imo) {
  return api.get(`/vessels/${cleanImo(imo)}/risk`)
}

/** Recalculate risk score breakdown */
export async function calculateRisk(imo) {
  return api.post(`/vessels/${cleanImo(imo)}/risk/calculate`)
}

/** Screen vessel against sanctions lists */
export async function screenSanctions(imo) {
  return api.post(`/vessels/${cleanImo(imo)}/screen`)
}

/** Generate investigation report */
export async function generateReport(imo, format = 'pdf', sections = null) {
  const body = { format }
  if (sections) body.sections = sections
  return api.post(`/vessels/${cleanImo(imo)}/report`, body)
}

export default api
