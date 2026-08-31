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
  const [isSearching, setIsSearching] = useState(false)
  const inputRef = useRef(null)
  const listRef = useRef(null)

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Search immediately (useVessels hook handles debouncing)
  useEffect(() => {
    if (query.length >= 2) {
      setIsSearching(true)
      onSearch(query)
      const timer = setTimeout(() => setIsSearching(false), 350)
      return () => clearTimeout(timer)
    } else {
      setIsSearching(false)
      onSearch('')
    }
  }, [query, onSearch])

  // Reset active index and clear searching when results change
  useEffect(() => {
    setActiveIndex(0)
    setIsSearching(false)
  }, [results])

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIndex((prev) => Math.min(prev + 1, Math.max(0, results.length - 1)))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIndex((prev) => Math.max(prev - 1, 0))
      } else if (e.key === 'Enter' && results.length > 0) {
        e.preventDefault()
        const selected = results[Math.min(activeIndex, results.length - 1)] || results[0]
        if (selected) onSelect(selected)
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
    <div className="search-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label="Search vessels">
      <div
        className="search-modal glass-panel"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="search-input-wrapper">
          <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={results.length > 0}
            aria-controls="search-results-list"
            aria-autocomplete="list"
            aria-activedescendant={results.length > 0 ? `search-result-${activeIndex}` : undefined}
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
          <ul id="search-results-list" className="search-results" ref={listRef} role="listbox" aria-label="Vessel search results">
            {results.map((vessel, i) => (
              <li
                key={vessel.id}
                id={`search-result-${i}`}
                role="option"
                aria-selected={i === activeIndex}
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
        {query.length >= 2 && results.length === 0 && !isSearching && (
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
