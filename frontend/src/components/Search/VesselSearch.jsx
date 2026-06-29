/* ═══════════════════════════════════════════════════════════════
   VesselSearch — Command-palette style vessel search (Ctrl+K)
   Glassmorphism modal with debounced autocomplete.
   ═══════════════════════════════════════════════════════════════ */

import { useState, useEffect, useRef, useCallback } from 'react'
import { getRiskColor, getRiskLabel } from '../../utils/riskColors'
import { getVesselColor } from '../../utils/vesselTypes'
import './VesselSearch.css'

export default function VesselSearch({ onSearch, results = [], onSelect, onClose }) {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef(null)
  const listRef = useRef(null)

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Search immediately (useVessels hook handles debouncing)
  useEffect(() => {
    if (query.length >= 2) {
      onSearch(query)
    } else {
      onSearch('')
    }
  }, [query, onSearch])

  // Reset active index when results change
  useEffect(() => {
    setActiveIndex(0)
  }, [results])

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIndex((prev) => Math.min(prev + 1, results.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIndex((prev) => Math.max(prev - 1, 0))
      } else if (e.key === 'Enter' && results.length > 0) {
        e.preventDefault()
        onSelect(results[activeIndex])
      } else if (e.key === 'Escape') {
        onClose()
      }
    },
    [results, activeIndex, onSelect, onClose]
  )

  // Scroll active item into view
  useEffect(() => {
    const activeEl = listRef.current?.children[activeIndex]
    activeEl?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  return (
    <div className="search-overlay" onClick={onClose}>
      <div
        className="search-modal glass-panel"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="search-input-wrapper">
          <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            className="search-input"
            placeholder="Search vessels by name, IMO, or MMSI..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <kbd className="search-kbd">ESC</kbd>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <ul className="search-results" ref={listRef}>
            {results.map((vessel, i) => (
              <li
                key={vessel.id}
                className={`search-result-item ${i === activeIndex ? 'active' : ''}`}
                onClick={() => onSelect(vessel)}
                onMouseEnter={() => setActiveIndex(i)}
              >
                <div className="search-result-left">
                  <span
                    className="search-result-dot"
                    style={{ background: getVesselColor(vessel.type) }}
                  />
                  <div className="search-result-info">
                    <span className="search-result-name">{vessel.name}</span>
                    <span className="search-result-meta">
                      {vessel.flag?.emoji} {vessel.type} · {vessel.imo}
                    </span>
                  </div>
                </div>
                <div className="search-result-right">
                  <span
                    className="search-result-risk"
                    style={{ color: getRiskColor(vessel.riskScore) }}
                  >
                    {vessel.riskScore}
                  </span>
                  <span className="search-result-risk-label">
                    {getRiskLabel(vessel.riskScore)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* Empty state */}
        {query.length >= 2 && results.length === 0 && (
          <div className="search-empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="40" height="40">
              <path d="M9.172 14.828a4 4 0 005.656 0M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>No vessels found for &ldquo;{query}&rdquo;</p>
          </div>
        )}

        {/* Hint */}
        {query.length < 2 && (
          <div className="search-hint">
            <span>Type at least 2 characters to search</span>
            <div className="search-hint-shortcuts">
              <span><kbd>↑↓</kbd> Navigate</span>
              <span><kbd>↵</kbd> Select</span>
              <span><kbd>esc</kbd> Close</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
