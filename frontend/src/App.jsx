import { useState, useEffect, useCallback, useMemo } from 'react'
import VesselMap from './components/Map/VesselMap'
import VesselPanel from './components/VesselDetail/VesselPanel'
import VesselSearch from './components/Search/VesselSearch'
import Navbar from './components/common/Navbar'
import Sidebar from './components/common/Sidebar'
import LoadingSpinner from './components/common/LoadingSpinner'
import useVessels from './hooks/useVessels'

export default function App() {
  const {
    vessels,
    searchResults,
    selectedVessel,
    loading,
    wsConnected,
    searchVessels,
    selectVessel,
    clearSelection,
  } = useVessels()

  const [searchOpen, setSearchOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [filters, setFilters] = useState({
    types: ['cargo', 'tanker', 'fishing', 'passenger', 'other'],
    riskMin: 0,
    riskMax: 100,
  })

  // ── Keyboard shortcuts ─────────────────────────────────────
  useEffect(() => {
    function handleKeyDown(e) {
      // Ctrl+K / Cmd+K → open search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen((prev) => !prev)
      }
      // Escape → close panels
      if (e.key === 'Escape') {
        if (searchOpen) {
          setSearchOpen(false)
        } else if (sidebarOpen) {
          setSidebarOpen(false)
        } else if (selectedVessel) {
          clearSelection()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [searchOpen, sidebarOpen, selectedVessel, clearSelection])

  // ── Filter vessels ─────────────────────────────────────────
  const filteredVessels = useMemo(() => {
    const isAllTypes =
      filters.types.length >= 5 &&
      ['cargo', 'tanker', 'fishing', 'passenger', 'other'].every((t) =>
        filters.types.includes(t)
      )
    const isDefaultRisk = (filters.riskMin ?? 0) <= 0 && (filters.riskMax ?? 100) >= 100

    // Fast-path: if no filters are actively restricting the dataset, return
    // the original vessels array reference directly to avoid cloning 1500 elements.
    if (isAllTypes && isDefaultRisk) {
      return vessels
    }

    const selectedTypes = new Set(filters.types)
    return vessels.filter((v) => {
      if (!selectedTypes.has(v.type)) return false
      const riskScore = v.riskScore ?? 0
      if (riskScore < filters.riskMin || riskScore > filters.riskMax) return false
      return true
    })
  }, [vessels, filters])

  // ── Handlers ───────────────────────────────────────────────
  const handleVesselClick = useCallback(
    (vessel) => {
      selectVessel(vessel)
    },
    [selectVessel]
  )

  const handleSearchSelect = useCallback(
    (vessel) => {
      selectVessel(vessel)
      setSearchOpen(false)
    },
    [selectVessel]
  )

  return (
    <>
      <Navbar
        vesselCount={filteredVessels.length}
        wsConnected={wsConnected}
        onSearchClick={() => setSearchOpen(true)}
        onSidebarToggle={() => setSidebarOpen((prev) => !prev)}
      />

      <div className="map-container">
        <VesselMap
          vessels={filteredVessels}
          selectedVessel={selectedVessel}
          onVesselClick={handleVesselClick}
        />
      </div>

      <Sidebar
        open={sidebarOpen}
        filters={filters}
        onFiltersChange={setFilters}
        vesselCount={filteredVessels.length}
        totalCount={vessels.length}
        onClose={() => setSidebarOpen(false)}
      />

      {selectedVessel && (
        <VesselPanel
          vessel={selectedVessel}
          onClose={clearSelection}
        />
      )}

      {searchOpen && (
        <VesselSearch
          onSearch={searchVessels}
          results={searchResults}
          onSelect={handleSearchSelect}
          onClose={() => setSearchOpen(false)}
        />
      )}

      {loading && (
        <div style={{
          position: 'absolute',
          inset: 0,
          top: '56px',
          backgroundColor: 'var(--bg-deep)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <LoadingSpinner text="Fetching vessel telemetry..." />
        </div>
      )}
    </>
  )
}
