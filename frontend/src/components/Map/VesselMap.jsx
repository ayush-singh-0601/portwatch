import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { MapContainer, TileLayer, useMapEvents } from 'react-leaflet'
import VesselMarker from './VesselMarker'
import 'leaflet/dist/leaflet.css'
import './VesselMap.css'

const MAX_MARKERS_BY_ZOOM = [
  { zoom: 3, limit: 450 },
  { zoom: 5, limit: 700 },
  { zoom: 7, limit: 1000 },
  { zoom: 18, limit: 1400 },
]

function isValidPosition(vessel) {
  return (
    Number.isFinite(Number(vessel.position?.lat)) &&
    Number.isFinite(Number(vessel.position?.lon))
  )
}

function readViewport(map) {
  const bounds = map.getBounds()
  return {
    north: bounds.getNorth(),
    south: bounds.getSouth(),
    east: bounds.getEast(),
    west: bounds.getWest(),
    zoom: map.getZoom(),
  }
}

export function isInsideViewport(vessel, viewport) {
  if (!viewport) return true

  const lat = Number(vessel?.position?.lat)
  const lon = Number(vessel?.position?.lon)
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false

  const inLatitude = lat >= viewport.south && lat <= viewport.north
  if (!inLatitude) return false

  const span = viewport.east - viewport.west
  if (span >= 360) return true

  // Handle both continuous Leaflet coords (where east > west even past 180)
  // and wrapped bounds (where east < west across antimeridian)
  const effectiveSpan = span >= 0 ? span : span + 360
  if (effectiveSpan >= 360) return true

  const offset = ((lon - viewport.west) % 360 + 360) % 360
  return offset <= effectiveSpan
}

function markerLimitForZoom(zoom = 3) {
  return MAX_MARKERS_BY_ZOOM.find((entry) => zoom <= entry.zoom)?.limit ?? 1400
}

function compareMarkerPriority(a, b) {
  const riskDelta = (b.riskScore ?? 0) - (a.riskScore ?? 0)
  if (riskDelta !== 0) return riskDelta

  // Date.parse avoids constructing intermediate Date objects inside the
  // O(N log N) sort comparator, eliminating thousands of GC allocations
  // on every viewport pan, zoom, or live telemetry update.
  const timeB = typeof b.lastSeen === 'number' ? b.lastSeen : (Date.parse(b.lastSeen) || 0)
  const timeA = typeof a.lastSeen === 'number' ? a.lastSeen : (Date.parse(a.lastSeen) || 0)
  return timeB - timeA
}

function MapResizeHandler() {
  const map = useMapEvents({})
  useEffect(() => {
    const container = map.getContainer()
    if (!container) return
    let active = true
    const obs = new ResizeObserver(() => {
      if (active && map && map.getContainer()) {
        try {
          map.invalidateSize()
        } catch {
          // Ignore errors during container destruction
        }
      }
    })
    obs.observe(container)
    return () => {
      active = false
      obs.disconnect()
    }
  }, [map])

  return null
}

function MapViewportTracker({ onViewportChange }) {
  const updateViewport = useCallback(
    (map) => {
      onViewportChange(readViewport(map))
    },
    [onViewportChange]
  )

  const map = useMapEvents({
    load: () => updateViewport(map),
    moveend: () => updateViewport(map),
    zoomend: () => updateViewport(map),
  })

  useEffect(() => {
    updateViewport(map)
  }, [map, updateViewport])

  return null
}

function MapSelectionFlyer({ selectedVessel }) {
  const map = useMapEvents({})
  const lastFlownIdRef = useRef(null)

  useEffect(() => {
    if (!selectedVessel) {
      lastFlownIdRef.current = null
      return
    }
    if (!isValidPosition(selectedVessel)) return

    if (selectedVessel.id !== lastFlownIdRef.current) {
      lastFlownIdRef.current = selectedVessel.id
      const lat = Number(selectedVessel.position.lat)
      const lon = Number(selectedVessel.position.lon)
      map.flyTo([lat, lon], Math.max(map.getZoom(), 6), {
        duration: 0.8,
      })
    }
  }, [map, selectedVessel])

  return null
}

function VesselMarkerLayer({ vessels, selectedVessel, onVesselClick, viewport }) {
  const renderedVessels = useMemo(() => {
    const selectedId = selectedVessel?.id
    const candidates = vessels.filter(
      (vessel) =>
        isValidPosition(vessel) &&
        (isInsideViewport(vessel, viewport) || vessel.id === selectedId)
    )
    const limit = markerLimitForZoom(viewport?.zoom)

    if (candidates.length <= limit) return candidates

    const selected = selectedId
      ? candidates.find((vessel) => vessel.id === selectedId)
      : null
    const prioritized = [...candidates]
      .sort(compareMarkerPriority)
      .slice(0, selected ? limit - 1 : limit)

    if (selected && !prioritized.some((vessel) => vessel.id === selected.id)) {
      prioritized.push(selected)
    }

    return prioritized
  }, [vessels, selectedVessel?.id, viewport])

  return (
    <>
      {renderedVessels.map((vessel) => (
        <VesselMarker
          key={vessel.id}
          vessel={vessel}
          isSelected={selectedVessel?.id === vessel.id}
          onClick={onVesselClick}
        />
      ))}
    </>
  )
}

export default function VesselMap({ vessels = [], selectedVessel, onVesselClick }) {
  const [viewport, setViewport] = useState(null)

  return (
    <MapContainer
      center={[20, 0]}
      zoom={3}
      minZoom={2}
      maxZoom={19}
      zoomControl={true}
      className="vessel-map"
      worldCopyJump={true}
      preferCanvas={true}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
        subdomains="abcd"
        maxZoom={19}
      />

      <MapResizeHandler />
      <MapViewportTracker onViewportChange={setViewport} />
      <MapSelectionFlyer selectedVessel={selectedVessel} />
      <VesselMarkerLayer
        vessels={vessels}
        selectedVessel={selectedVessel}
        onVesselClick={onVesselClick}
        viewport={viewport}
      />
    </MapContainer>
  )
}
