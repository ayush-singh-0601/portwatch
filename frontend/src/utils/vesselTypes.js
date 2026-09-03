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
 * Map numerical AIS ITU ship type code (0-99) to standard category.
 */
export function mapShipTypeCodeToCategory(code) {
  const num = Number(code)
  if (!Number.isFinite(num)) return 'other'
  if (num === 30) return 'fishing'
  if (num === 35 || num === 55) return 'military'
  if (num >= 60 && num <= 69) return 'passenger'
  if (num >= 70 && num <= 79) return 'cargo'
  if (num >= 80 && num <= 89) return 'tanker'
  return 'other'
}

