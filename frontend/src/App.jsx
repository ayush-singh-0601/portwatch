import { useState, useEffect, useCallback } from 'react'
import VesselMap from './components/Map/VesselMap'
import VesselPanel from './components/VesselDetail/VesselPanel'
import VesselSearch from './components/Search/VesselSearch'
import Navbar from './components/common/Navbar'
import Sidebar from './components/common/Sidebar'
import useVessels from './hooks/useVessels'

export default function App() {
  const {
    vessels,
    searchResults,
    selectedVessel,
    loading,
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
        } else if (selectedVessel) {
          clearSelection()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [searchOpen, selectedVessel, clearSelection])

  // ── Filter vessels ─────────────────────────────────────────
  const filteredVessels = vessels.filter((v) => {
    if (!filters.types.includes(v.type)) return false
    if (v.riskScore < filters.riskMin || v.riskScore > filters.riskMax) return false
    return true
  })

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
    </>
  )
}
