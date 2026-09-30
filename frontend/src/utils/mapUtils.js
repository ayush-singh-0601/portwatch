
export function roundedHeading(heading) {
  const value = Number(heading)
  if (!Number.isFinite(value)) return 0
  const normalized = ((value % 360) + 360) % 360
  return (Math.round(normalized / 10) * 10) % 360
}

export function riskBand(score) {
  if (score >= 75) return 'critical'
  if (score >= 50) return 'high'
  if (score >= 25) return 'medium'
  return 'low'
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
