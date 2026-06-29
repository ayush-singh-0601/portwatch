import { memo, useMemo } from 'react'
import { Marker, Tooltip } from 'react-leaflet'
import L from 'leaflet'
import { getVesselColor, getVesselLabel } from '../../utils/vesselTypes'
import { getRiskColor, getRiskLabelShort } from '../../utils/riskColors'

const iconCache = new Map()

function roundedHeading(heading) {
  const value = Number(heading)
  if (!Number.isFinite(value)) return 0
  return Math.round(value / 10) * 10
}

function createVesselIcon(vesselType, heading, isSelected) {
  const color = getVesselColor(vesselType)
  const size = isSelected ? 30 : 22
  const rotation = roundedHeading(heading)
  const cacheKey = `${vesselType}|${rotation}|${isSelected}`
  const cached = iconCache.get(cacheKey)
  if (cached) return cached

  const html = `
    <div class="vessel-icon-shell" style="--vessel-color: ${color}; --vessel-size: ${size}px; transform: rotate(${rotation}deg);">
      <svg width="${size}" height="${size}" viewBox="0 0 32 32" aria-hidden="true">
        <path d="M16 4 L24 26 L16 21 L8 26 Z"
          fill="${color}"
          stroke="${isSelected ? '#ffffff' : color}"
          stroke-width="${isSelected ? 2 : 1}"
          stroke-linejoin="round"/>
      </svg>
    </div>
  `

  const icon = L.divIcon({
    html,
    className: `vessel-marker ${isSelected ? 'vessel-marker-selected' : ''}`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    tooltipAnchor: [size / 2 + 4, 0],
  })

  iconCache.set(cacheKey, icon)
  return icon
}

function VesselMarker({ vessel, isSelected, onClick }) {
  const lat = Number(vessel.position?.lat)
  const lon = Number(vessel.position?.lon)

  const icon = useMemo(
    () => createVesselIcon(vessel.type, vessel.heading, isSelected),
    [vessel.type, vessel.heading, isSelected]
  )
  const position = useMemo(() => [lat, lon], [lat, lon])
  const eventHandlers = useMemo(
    () => ({
      click: () => onClick?.(vessel),
    }),
    [onClick, vessel]
  )

  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null

  const speed = Number(vessel.speed)
  const heading = Number(vessel.heading)

  return (
    <Marker
      position={position}
      icon={icon}
      eventHandlers={eventHandlers}
    >
      <Tooltip
        className="vessel-tooltip"
        direction="top"
        offset={[0, -14]}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontWeight: 700, fontSize: '0.875rem' }}>{vessel.name}</span>
            <span style={{ fontSize: '0.9rem' }}>{vessel.flag?.emoji}</span>
          </div>
          <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            <span style={{
              color: getVesselColor(vessel.type),
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: '0.625rem',
              letterSpacing: '0.06em'
            }}>
              {getVesselLabel(vessel.type)}
            </span>
            <span>{Number.isFinite(speed) ? speed.toFixed(1) : '0.0'} kn</span>
            <span>{Number.isFinite(heading) ? Math.round(heading) : 0} deg</span>
          </div>
          {vessel.riskScore > 60 && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.625rem',
              fontWeight: 700,
              color: getRiskColor(vessel.riskScore),
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              marginTop: '2px',
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: getRiskColor(vessel.riskScore),
                display: 'inline-block',
              }}/>
              {getRiskLabelShort(vessel.riskScore)} RISK - {vessel.riskScore}
            </div>
          )}
        </div>
      </Tooltip>
    </Marker>
  )
}

export default memo(VesselMarker)
