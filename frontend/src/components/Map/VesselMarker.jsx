import { useMemo } from 'react'
import { Marker, Tooltip } from 'react-leaflet'
import L from 'leaflet'
import { getVesselColor, getVesselLabel } from '../../utils/vesselTypes'
import { getRiskColor, getRiskLabelShort } from '../../utils/riskColors'

function createVesselIcon(vessel, isSelected) {
  const color = getVesselColor(vessel.type)
  const size = isSelected ? 32 : 24
  const glowOpacity = isSelected ? 0.7 : 0.4
  const rotation = vessel.heading || 0

  const svgHtml = `
    <div style="transform: rotate(${rotation}deg); width: ${size}px; height: ${size}px; transition: transform 0.3s ease;">
      <svg width="${size}" height="${size}" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <filter id="glow-${vessel.id}" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="${isSelected ? 4 : 2}" flood-color="${color}" flood-opacity="${glowOpacity}"/>
          </filter>
        </defs>
        <g filter="url(#glow-${vessel.id})">
          <path d="M16 4 L24 26 L16 21 L8 26 Z"
                fill="${color}"
                fill-opacity="0.9"
                stroke="${isSelected ? '#fff' : color}"
                stroke-width="${isSelected ? 1.5 : 0.8}"
                stroke-linejoin="round"/>
        </g>
        ${isSelected ? `
        <circle cx="16" cy="16" r="14" fill="none" stroke="${color}" stroke-width="1" opacity="0.4">
          <animate attributeName="r" values="14;18;14" dur="2s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.4;0.1;0.4" dur="2s" repeatCount="indefinite"/>
        </circle>` : ''}
      </svg>
    </div>
  `

  return L.divIcon({
    html: svgHtml,
    className: `vessel-marker ${isSelected ? 'vessel-marker-selected' : ''}`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    tooltipAnchor: [size / 2 + 4, 0],
  })
}

export default function VesselMarker({ vessel, isSelected, onClick }) {
  const icon = useMemo(
    () => createVesselIcon(vessel, isSelected),
    [vessel.id, vessel.type, vessel.heading, isSelected]
  )

  if (!vessel.position?.lat || !vessel.position?.lon) return null

  return (
    <Marker
      position={[vessel.position.lat, vessel.position.lon]}
      icon={icon}
      eventHandlers={{
        click: () => onClick?.(vessel),
      }}
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
            <span>{vessel.speed?.toFixed(1)} kn</span>
            <span>{vessel.heading}°</span>
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
              {getRiskLabelShort(vessel.riskScore)} RISK — {vessel.riskScore}
            </div>
          )}
        </div>
      </Tooltip>
    </Marker>
  )
}
