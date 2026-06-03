import { useState, useCallback, useEffect, useRef } from 'react'
import { MOCK_VESSELS } from '../utils/mockData'
import useWebSocket from './useWebSocket'

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
      const response = await fetch('/api/vessels/enriched')
      if (!response.ok) throw new Error('Backend unavailable')
      const data = await response.json()

      // The enriched endpoint returns a flat JSON array — exactly
      // the shape our components expect.
      setVessels(data)
    } catch {
      // Fallback to mock data
      console.log('[Vessels] Using mock data (backend unavailable)')
      setVessels(MOCK_VESSELS)
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
        // Try to find index of existing vessel by MMSI or IMO
        let idx = mmsiToVesselIdx[key] ?? imoToVesselIdx[key]
        
        if (idx !== undefined) {
          // Update existing vessel
          next[idx] = {
            ...next[idx],
            position: {
              lat: update.lat,
              lon: update.lon,
            },
            heading: update.heading ?? next[idx].heading,
            speed: update.speed ?? next[idx].speed,
            lastSeen: update.timestamp || new Date().toISOString(),
          }
        } else {
          // It's a new vessel not currently in the state! Synthesize it
          const mmsiVal = isNaN(Number(key)) ? null : String(key)
          // Avoid adding duplicates during the loop
          if (mmsiVal && mmsiToVesselIdx[mmsiVal] === undefined) {
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
                lat: update.lat,
                lon: update.lon,
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
        const results = vessels.filter(
          (v) =>
            v.name?.toLowerCase().includes(q) ||
            String(v.imo).toLowerCase().includes(q) ||
            String(v.mmsi).includes(q) ||
            v.type?.toLowerCase().includes(q) ||
            v.flag?.name?.toLowerCase().includes(q) ||
            v.destination?.toLowerCase().includes(q)
        )
        setSearchResults(results)
      }, 300)
    },
    [vessels]
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
