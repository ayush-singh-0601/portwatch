import { useState, useCallback, useEffect, useRef } from 'react'
import { MOCK_VESSELS } from '../utils/mockData'

/**
 * Custom hook for vessel data management.
 * Uses mock data when the backend is unavailable.
 */
export default function useVessels() {
  const [vessels, setVessels] = useState([])
  const [searchResults, setSearchResults] = useState([])
  const [selectedVessel, setSelectedVessel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const searchTimerRef = useRef(null)

  // ── Load vessels (falls back to mock) ──────────────────────
  const fetchVessels = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/vessels')
      if (!response.ok) throw new Error('Backend unavailable')
      const data = await response.json()
      setVessels(data)
    } catch {
      // Fallback to mock data
      console.log('[Vessels] Using mock data (backend unavailable)')
      setVessels(MOCK_VESSELS)
    } finally {
      setLoading(false)
    }
  }, [])

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
            v.name.toLowerCase().includes(q) ||
            v.imo.toLowerCase().includes(q) ||
            v.mmsi.includes(q) ||
            v.type.toLowerCase().includes(q) ||
            v.flag.name.toLowerCase().includes(q) ||
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
          (v) => v.id === vesselOrId || v.imo === vesselOrId
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
    searchVessels,
    selectVessel,
    clearSelection,
    refetch: fetchVessels,
  }
}
