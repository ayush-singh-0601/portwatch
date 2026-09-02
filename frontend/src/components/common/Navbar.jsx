import { useState, useEffect } from 'react'
import './Navbar.css'

export default function Navbar({
  vesselCount = 0,
  wsConnected = false,
  onSearchClick,
  onSidebarToggle,
}) {
  const [displayCount, setDisplayCount] = useState(0)
  const [shortcutText, setShortcutText] = useState('⌘K')

  // Animated counter
  useEffect(() => {
    if (displayCount === vesselCount) return
    const diff = vesselCount - displayCount
    const step = Math.max(1, Math.abs(Math.floor(diff / 10)))
    const timer = setTimeout(() => {
      setDisplayCount((prev) =>
        diff > 0 ? Math.min(prev + step, vesselCount) : Math.max(prev - step, vesselCount)
      )
    }, 30)
    return () => clearTimeout(timer)
  }, [displayCount, vesselCount])

  // Detect platform for keyboard shortcut indicator
  useEffect(() => {
    const isMacPlatform = /Mac|iPod|iPhone|iPad/.test(navigator.userAgent || navigator.platform || '')
    setShortcutText(isMacPlatform ? '⌘K' : 'Ctrl+K')
  }, [])

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <button className="navbar-menu-btn" onClick={onSidebarToggle} aria-label="Toggle filters">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
        </button>
        <div className="navbar-brand">
          <div className="navbar-logo">
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="13" stroke="currentColor" strokeWidth="1.5" opacity="0.3"/>
              <path d="M16 5L16 19M11 14L16 19L21 14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 24Q16 28 24 24" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" fill="none"/>
            </svg>
          </div>
          <div className="navbar-title">
            <span className="navbar-title-port">Port</span>
            <span className="navbar-title-watch">Watch</span>
          </div>
          <span className="navbar-subtitle">Maritime Intelligence</span>
        </div>
      </div>

      <div className="navbar-center">
        <div
          className="navbar-stat"
          title={wsConnected ? 'Live WebSocket telemetry active' : 'Offline / Polling mode'}
          aria-label={wsConnected ? 'Live WebSocket telemetry active' : 'Offline / Polling mode'}
        >
          <div
            className="navbar-stat-dot"
            style={{
              background: wsConnected ? 'var(--success, #10b981)' : 'var(--warning, #f59e0b)',
              boxShadow: wsConnected ? '0 0 8px #10b981' : 'none',
            }}
          />
          <span className="navbar-stat-count">{displayCount}</span>
          <span className="navbar-stat-label">
            {wsConnected ? 'Live Vessels' : 'Tracked Vessels'}
          </span>
        </div>
      </div>

      <div className="navbar-right">
        <button className="navbar-search-btn" onClick={onSearchClick} title={`Search vessels (${shortcutText})`}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="7.5" cy="7.5" r="5.5" stroke="currentColor" strokeWidth="1.8"/>
            <path d="M12 12L16 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
          <span className="navbar-search-label">Search</span>
          <kbd className="navbar-kbd">{shortcutText}</kbd>
        </button>

        <button
          className="btn-icon btn-ghost navbar-icon-btn"
          title="Settings (coming soon)"
          aria-disabled="true"
          aria-label="Settings (coming soon)"
          style={{ opacity: 0.4, cursor: 'not-allowed' }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="2.5" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M9 1.5v2M9 14.5v2M1.5 9h2M14.5 9h2M3.4 3.4l1.4 1.4M13.2 13.2l1.4 1.4M3.4 14.6l1.4-1.4M13.2 4.8l1.4-1.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </button>
      </div>
    </nav>
  )
}
