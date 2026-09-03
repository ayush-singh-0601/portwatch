/* ═══════════════════════════════════════════════════════════════
   LoadingSpinner — Animated compass/ship-wheel spinner
   ═══════════════════════════════════════════════════════════════ */

import './LoadingSpinner.css'

export default function LoadingSpinner({ text = 'Loading...', size = 'md' }) {
  const pixelSize = size === 'sm' ? 24 : size === 'lg' ? 72 : 48

  return (
    <div className={`loading-spinner loading-spinner-${size}`} role="status" aria-live="polite">
      <svg
        className="spinner-icon"
        viewBox="0 0 100 100"
        width={pixelSize}
        height={pixelSize}
        aria-hidden="true"
      >
        {/* Outer ring */}
        <circle
          cx="50" cy="50" r="45"
          fill="none"
          stroke="var(--border)"
          strokeWidth="2"
        />
        {/* Spinning arc */}
        <circle
          cx="50" cy="50" r="45"
          fill="none"
          stroke="var(--accent)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="80 200"
          className="spinner-arc"
        />
        {/* Compass cross */}
        <line x1="50" y1="12" x2="50" y2="32" stroke="var(--text-muted)" strokeWidth="1.5" />
        <line x1="50" y1="68" x2="50" y2="88" stroke="var(--text-muted)" strokeWidth="1.5" />
        <line x1="12" y1="50" x2="32" y2="50" stroke="var(--text-muted)" strokeWidth="1.5" />
        <line x1="68" y1="50" x2="88" y2="50" stroke="var(--text-muted)" strokeWidth="1.5" />
        {/* Center dot */}
        <circle cx="50" cy="50" r="3" fill="var(--accent)" />
        {/* North indicator */}
        <polygon points="50,8 46,18 54,18" fill="var(--accent)" className="spinner-north" />
      </svg>
      {text && <span className="spinner-text">{text}</span>}
    </div>
  )
}
