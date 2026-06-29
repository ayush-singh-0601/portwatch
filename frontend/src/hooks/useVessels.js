import { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import { MOCK_VESSELS } from '../utils/mockData'
import useWebSocket from './useWebSocket'

const INITIAL_VESSEL_LIMIT = 1000
const ACTIVE_POSITION_MINUTES = 720
const MAX_TRACKED_VESSELS = 1500
const MAX_SEARCH_RESULTS = 50

function isFiniteCoordinate(value) {
  return Number.isFinite(Number(value))
}

function normalizeVessel(vessel) {
  const id = String(vessel.id ?? vessel.imo ?? vessel.mmsi ?? '')
  if (!id) return null

  return {
    ...vessel,
    id,
    imo: vessel.imo != null ? String(vessel.imo) : null,
    mmsi: vessel.mmsi != null ? String(vessel.mmsi) : null,
    type: vessel.type || 'other',
    riskScore: Number(vessel.riskScore ?? 0),
  }
}

function normalizeVessels(data) {
  const seen = new Set()
  const result = []

  for (const raw of Array.isArray(data) ? data : []) {
    const vessel = normalizeVessel(raw)
    if (!vessel || seen.has(vessel.id)) continue
    seen.add(vessel.id)
    result.push(vessel)
    if (result.length >= MAX_TRACKED_VESSELS) break
  }

  return result
}

/**
 * Custom hook for vessel data management.
 * Fetches enriched vessel data from the API (with embedded position,
 * risk, ownership, and sanctions) and merges live WebSocket updates.
 */
export default function useVessels() {
  const [vessels, setVessels] = useState([])
  const [searchResults, setSearchResults] = useState([])
  const [selectedVessel, setSelectedVessel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const searchTimerRef = useRef(null)

  // WebSocket for live position updates
  const { positions: livePositions, isConnected: wsConnected } = useWebSocket()

  // ── Load vessels (falls back to mock) ──────────────────────
  const fetchVessels = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({
        limit: String(INITIAL_VESSEL_LIMIT),
        active_minutes: String(ACTIVE_POSITION_MINUTES),
        include_unregistered: 'true',
      })
      const response = await fetch(`/api/vessels/enriched?${params}`)
      if (!response.ok) throw new Error('Backend unavailable')
      const data = await response.json()

      // The enriched endpoint returns a flat JSON array — exactly
      // the shape our components expect.
      setVessels(normalizeVessels(data))
    } catch {
      // Fallback to mock data
      console.log('[Vessels] Using mock data (backend unavailable)')
      setVessels(normalizeVessels(MOCK_VESSELS))
    } finally {
      setLoading(false)
    }
  }, [])

  // ── Merge live WebSocket position updates ──────────────────
  useEffect(() => {
    if (!livePositions || Object.keys(livePositions).length === 0) return

    setVessels((prev) => {
      const next = [...prev]
      const mmsiToVesselIdx = {}
      const imoToVesselIdx = {}
      
      next.forEach((v, idx) => {
        if (v.mmsi) mmsiToVesselIdx[String(v.mmsi)] = idx
        if (v.imo) imoToVesselIdx[String(v.imo)] = idx
      })

      Object.entries(livePositions).forEach(([key, update]) => {
        if (!isFiniteCoordinate(update.lat) || !isFiniteCoordinate(update.lon)) return

        // Try to find index of existing vessel by MMSI or IMO
        let idx = mmsiToVesselIdx[key] ?? imoToVesselIdx[key]
        
        if (idx !== undefined) {
          // Update existing vessel
          next[idx] = {
            ...next[idx],
            position: {
              lat: Number(update.lat),
              lon: Number(update.lon),
            },
            heading: update.heading ?? next[idx].heading,
            speed: update.speed ?? next[idx].speed,
            lastSeen: update.timestamp || new Date().toISOString(),
          }
        } else {
          // It's a new vessel not currently in the state! Synthesize it
          const mmsiVal = isNaN(Number(key)) ? null : String(key)
          // Avoid adding duplicates during the loop
          if (mmsiVal && mmsiToVesselIdx[mmsiVal] === undefined && next.length < MAX_TRACKED_VESSELS) {
            const newVessel = {
              id: mmsiVal,
              imo: null,
              mmsi: mmsiVal,
              name: `MMSI ${mmsiVal}`,
              type: 'other',
              flag: { code: 'UNK', name: 'Unknown', emoji: '🏳️' },
              riskScore: 0,
              riskFactors: [],
              position: {
                lat: Number(update.lat),
                lon: Number(update.lon),
              },
              heading: update.heading ?? 0,
              speed: update.speed ?? 0,
              lastSeen: update.timestamp || new Date().toISOString(),
              ownership: {
                registeredOwner: null,
                beneficialOwner: null,
                operator: null,
                flagHistory: [],
              },
              sanctions: { matched: false, lists: [] }
            }
            next.push(newVessel)
            mmsiToVesselIdx[mmsiVal] = next.length - 1
          }
        }
      })
      
      return next
    })
  }, [livePositions])

  const searchIndex = useMemo(() => {
    return vessels.map((vessel) => ({
      vessel,
      text: [
        vessel.name,
        vessel.imo,
        vessel.mmsi,
        vessel.type,
        vessel.flag?.name,
        vessel.destination,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase(),
    }))
  }, [vessels])

  // ── Search with debounce ───────────────────────────────────
  const searchVessels = useCallback(
    (query) => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current)

      if (!query || query.trim().length === 0) {
        setSearchResults([])
        return
      }

      searchTimerRef.current = setTimeout(() => {
        const q = query.toLowerCase().trim()
        const results = []
        for (const entry of searchIndex) {
          if (!entry.text.includes(q)) continue
          results.push(entry.vessel)
          if (results.length >= MAX_SEARCH_RESULTS) break
        }
        setSearchResults(results)
      }, 300)
    },
    [searchIndex]
  )

  // ── Select vessel ──────────────────────────────────────────
  const selectVessel = useCallback(
    (vesselOrId) => {
      if (!vesselOrId) {
        setSelectedVessel(null)
        return
      }
      if (typeof vesselOrId === 'object') {
        setSelectedVessel(vesselOrId)
      } else {
        const found = vessels.find(
          (v) => v.id === vesselOrId || v.imo === String(vesselOrId)
        )
        setSelectedVessel(found || null)
      }
    },
    [vessels]
  )

  // ── Clear selection ────────────────────────────────────────
  const clearSelection = useCallback(() => {
    setSelectedVessel(null)
  }, [])

  // ── Initial load ───────────────────────────────────────────
  useEffect(() => {
    fetchVessels()
  }, [fetchVessels])

  // Cleanup
  useEffect(() => {
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    }
  }, [])

  return {
    vessels,
    searchResults,
    selectedVessel,
    loading,
    error,
    wsConnected,
    searchVessels,
    selectVessel,
    clearSelection,
    refetch: fetchVessels,
  }
}
