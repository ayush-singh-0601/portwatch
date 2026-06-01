/* ── Vessel Type Definitions ─────────────────────────────────── */

export const VESSEL_TYPES = {
  cargo: {
    label: 'Cargo',
    color: 'hsl(185, 70%, 48%)',
    colorVar: 'var(--accent)',
    badgeClass: 'badge-accent',
    dotClass: 'badge-dot-accent',
  },
  tanker: {
    label: 'Tanker',
    color: 'hsl(38, 92%, 55%)',
    colorVar: 'var(--warning)',
    badgeClass: 'badge-warning',
    dotClass: 'badge-dot-warning',
  },
  fishing: {
    label: 'Fishing',
    color: 'hsl(160, 60%, 45%)',
    colorVar: 'var(--success)',
    badgeClass: 'badge-success',
    dotClass: 'badge-dot-success',
  },
  passenger: {
    label: 'Passenger',
    color: 'hsl(240, 70%, 65%)',
    colorVar: 'var(--info)',
    badgeClass: 'badge-info',
    dotClass: 'badge-dot-info',
  },
  military: {
    label: 'Military',
    color: 'hsl(0, 85%, 55%)',
    colorVar: 'var(--danger)',
    badgeClass: 'badge-danger',
    dotClass: 'badge-dot-danger',
  },
  other: {
    label: 'Other',
    color: 'hsl(220, 12%, 55%)',
    colorVar: 'var(--text-secondary)',
    badgeClass: 'badge-muted',
    dotClass: '',
  },
}

/**
 * Get vessel color by type code
 */
export function getVesselColor(type) {
  return VESSEL_TYPES[type]?.color || VESSEL_TYPES.other.color
}

/**
 * Get vessel CSS variable color by type code
 */
export function getVesselColorVar(type) {
  return VESSEL_TYPES[type]?.colorVar || VESSEL_TYPES.other.colorVar
}

/**
 * Get vessel badge class by type code
 */
export function getVesselBadgeClass(type) {
  return VESSEL_TYPES[type]?.badgeClass || VESSEL_TYPES.other.badgeClass
}

/**
 * Get vessel label by type code
 */
export function getVesselLabel(type) {
  return VESSEL_TYPES[type]?.label || 'Unknown'
}

/**
 * Returns an SVG path string for a ship icon pointing up (heading 0).
 * The marker component applies rotation based on vessel heading.
 */
export function getVesselIcon(type) {
  const color = getVesselColor(type)
  return `
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <g filter="url(#glow)">
        <path d="M14 3 L22 22 L14 18 L6 22 Z" fill="${color}" fill-opacity="0.9" stroke="${color}" stroke-width="1" stroke-linejoin="round"/>
      </g>
      <defs>
        <filter id="glow" x="-2" y="-2" width="32" height="32">
          <feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="${color}" flood-opacity="0.5"/>
        </filter>
      </defs>
    </svg>
  `
}
