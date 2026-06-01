/* ── Risk Score Color Utilities ───────────────────────────────── */

/**
 * Returns a CSS color string based on risk score 0-100.
 *   0-30  → green (low risk)
 *  31-60  → amber (medium risk)
 *  61-100 → red   (high risk)
 */
export function getRiskColor(score) {
  if (score <= 30) return 'hsl(160, 60%, 45%)'    // success green
  if (score <= 60) return 'hsl(38, 92%, 55%)'     // warning amber
  return 'hsl(0, 85%, 55%)'                        // danger red
}

/**
 * Returns the CSS variable name for risk color.
 */
export function getRiskColorVar(score) {
  if (score <= 30) return 'var(--success)'
  if (score <= 60) return 'var(--warning)'
  return 'var(--danger)'
}

/**
 * Returns a risk label string.
 */
export function getRiskLabel(score) {
  if (score <= 30) return 'LOW RISK'
  if (score <= 60) return 'MEDIUM RISK'
  return 'HIGH RISK'
}

/**
 * Returns a short risk label.
 */
export function getRiskLabelShort(score) {
  if (score <= 30) return 'LOW'
  if (score <= 60) return 'MED'
  return 'HIGH'
}

/**
 * Returns a CSS gradient string for backgrounds based on risk.
 */
export function getRiskGradient(score) {
  if (score <= 30) {
    return 'linear-gradient(135deg, hsla(160, 60%, 45%, 0.15), hsla(160, 60%, 45%, 0.05))'
  }
  if (score <= 60) {
    return 'linear-gradient(135deg, hsla(38, 92%, 55%, 0.15), hsla(38, 92%, 55%, 0.05))'
  }
  return 'linear-gradient(135deg, hsla(0, 85%, 55%, 0.15), hsla(0, 85%, 55%, 0.05))'
}

/**
 * Returns glow shadow for risk badge.
 */
export function getRiskGlow(score) {
  if (score <= 30) return '0 0 12px hsla(160, 60%, 45%, 0.3)'
  if (score <= 60) return '0 0 12px hsla(38, 92%, 55%, 0.3)'
  return '0 0 20px hsla(0, 85%, 55%, 0.4), 0 0 40px hsla(0, 85%, 55%, 0.15)'
}

/**
 * Returns the badge CSS class for risk level.
 */
export function getRiskBadgeClass(score) {
  if (score <= 30) return 'badge-success'
  if (score <= 60) return 'badge-warning'
  return 'badge-danger'
}
