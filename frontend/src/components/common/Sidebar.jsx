/* ═══════════════════════════════════════════════════════════════
   Sidebar — Collapsible filter panel with glassmorphism
   ═══════════════════════════════════════════════════════════════ */

import { useCallback } from 'react'
import './Sidebar.css'

const VESSEL_TYPE_OPTIONS = [
  { value: 'cargo', label: 'Cargo', color: 'var(--accent)' },
  { value: 'tanker', label: 'Tanker', color: 'var(--warning)' },
  { value: 'fishing', label: 'Fishing', color: 'var(--success)' },
  { value: 'passenger', label: 'Passenger', color: 'hsl(240, 70%, 65%)' },
  { value: 'other', label: 'Other', color: 'var(--text-secondary)' },
]

export default function Sidebar({ open, filters, onFiltersChange, vesselCount, totalCount, onClose }) {
  const handleTypeToggle = useCallback(
    (type) => {
      const types = filters.types.includes(type)
        ? filters.types.filter((t) => t !== type)
        : [...filters.types, type]
      onFiltersChange({ ...filters, types })
    },
    [filters, onFiltersChange]
  )

  const handleRiskMinChange = useCallback(
    (e) => {
      const val = Math.min(Number(e.target.value), filters.riskMax)
      onFiltersChange({ ...filters, riskMin: val })
    },
    [filters, onFiltersChange]
  )

  const handleRiskMaxChange = useCallback(
    (e) => {
      const val = Math.max(Number(e.target.value), filters.riskMin)
      onFiltersChange({ ...filters, riskMax: val })
    },
    [filters, onFiltersChange]
  )

  const handleReset = useCallback(() => {
    onFiltersChange({
      types: ['cargo', 'tanker', 'fishing', 'passenger', 'other'],
      riskMin: 0,
      riskMax: 100,
    })
  }, [onFiltersChange])

  return (
    <aside className={`sidebar glass-panel ${open ? 'open' : ''}`}>
      {/* Header */}
      <div className="sidebar-header">
        <h3 className="sidebar-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
            <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
          </svg>
          Filters
        </h3>
        <button className="sidebar-close" onClick={onClose} aria-label="Close sidebar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Vessel count */}
      <div className="sidebar-count">
        <span className="sidebar-count-num">{vesselCount}</span>
        <span className="sidebar-count-label">of {totalCount} vessels</span>
      </div>

      {/* Quick Presets */}
      <div className="sidebar-section">
        <h4 className="sidebar-section-title">Quick Presets</h4>
        <div className="sidebar-presets">
          <button
            className="sidebar-preset-btn"
            onClick={() =>
              onFiltersChange({
                types: ['cargo', 'tanker', 'fishing', 'passenger', 'other'],
                riskMin: 0,
                riskMax: 100,
              })
            }
          >
            All Vessels
          </button>
          <button
            className="sidebar-preset-btn"
            onClick={() =>
              onFiltersChange({
                types: ['cargo', 'tanker', 'fishing', 'passenger', 'other'],
                riskMin: 50,
                riskMax: 100,
              })
            }
          >
            High Risk (50+)
          </button>
          <button
            className="sidebar-preset-btn"
            onClick={() =>
              onFiltersChange({
                types: ['tanker', 'cargo'],
                riskMin: 0,
                riskMax: 100,
              })
            }
          >
            Tankers & Cargo
          </button>
        </div>
      </div>

      {/* Vessel type filter */}
      <div className="sidebar-section">
        <h4 className="sidebar-section-title">Vessel Type</h4>
        <div className="sidebar-checkboxes">
          {VESSEL_TYPE_OPTIONS.map((opt) => (
            <label key={opt.value} className="sidebar-checkbox">
              <input
                type="checkbox"
                checked={filters.types.includes(opt.value)}
                onChange={() => handleTypeToggle(opt.value)}
              />
              <span className="sidebar-checkbox-dot" style={{ background: opt.color }} />
              <span className="sidebar-checkbox-label">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Risk score range */}
      <div className="sidebar-section">
        <h4 className="sidebar-section-title">Risk Score Range</h4>
        <div className="sidebar-range">
          <div className="sidebar-range-inputs">
            <label className="sidebar-range-field">
              <span>Min</span>
              <input
                type="number"
                min="0"
                max="100"
                value={filters.riskMin}
                onChange={handleRiskMinChange}
              />
            </label>
            <span className="sidebar-range-dash">–</span>
            <label className="sidebar-range-field">
              <span>Max</span>
              <input
                type="number"
                min="0"
                max="100"
                value={filters.riskMax}
                onChange={handleRiskMaxChange}
              />
            </label>
          </div>
          <div className="sidebar-range-bar">
            <div
              className="sidebar-range-fill"
              style={{
                left: `${filters.riskMin}%`,
                width: `${filters.riskMax - filters.riskMin}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Reset button */}
      <button className="btn-secondary sidebar-reset" onClick={handleReset}>
        Reset Filters
      </button>
    </aside>
  )
}
