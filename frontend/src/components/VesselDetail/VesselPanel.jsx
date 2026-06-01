import { useState } from 'react'
import RiskBadge from './RiskBadge'
import IdentityCard from './IdentityCard'
import OwnershipGraph from './OwnershipGraph'
import { getVesselBadgeClass, getVesselLabel } from '../../utils/vesselTypes'
import './VesselPanel.css'

const TABS = ['Overview', 'Ownership', 'Sanctions', 'History']

export default function VesselPanel({ vessel, onClose }) {
  const [activeTab, setActiveTab] = useState('Overview')

  if (!vessel) return null

  const timeSinceLastSeen = () => {
    if (!vessel.lastSeen) return 'Unknown'
    const diff = Date.now() - new Date(vessel.lastSeen).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'Just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  }

  return (
    <div className="vessel-panel animate-slideRight">
      {/* Close button */}
      <button className="vessel-panel-close" onClick={onClose} aria-label="Close panel">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M4 4L14 14M14 4L4 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
        </svg>
      </button>

      {/* Header */}
      <div className="vessel-panel-header">
        <div className="vessel-panel-header-top">
          <div className="vessel-panel-name-section">
            <h2 className="vessel-panel-name">{vessel.name}</h2>
            <div className="vessel-panel-flag">
              <span className="vessel-panel-flag-emoji">{vessel.flag?.emoji}</span>
              <span className="vessel-panel-flag-name">{vessel.flag?.name}</span>
            </div>
          </div>
          <RiskBadge score={vessel.riskScore} size={72} />
        </div>

        <div className="vessel-panel-ids">
          <span className="mono">{vessel.imo}</span>
          <span className="vessel-panel-id-sep">•</span>
          <span className="mono">MMSI {vessel.mmsi}</span>
        </div>

        <span className={`badge ${getVesselBadgeClass(vessel.type)}`}>
          {getVesselLabel(vessel.type)}
        </span>
      </div>

      <hr className="divider" />

      {/* Tabs */}
      <div className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={`tab-bar-item ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="vessel-panel-content">
        {activeTab === 'Overview' && (
          <div className="animate-fadeIn">
            <IdentityCard vessel={vessel} />

            <div className="vessel-panel-section">
              <h4 className="vessel-panel-section-title">Current Position</h4>
              <div className="vessel-panel-grid">
                <div className="vessel-panel-field">
                  <span className="label">Latitude</span>
                  <span className="mono">{vessel.position?.lat?.toFixed(4)}°</span>
                </div>
                <div className="vessel-panel-field">
                  <span className="label">Longitude</span>
                  <span className="mono">{vessel.position?.lon?.toFixed(4)}°</span>
                </div>
                <div className="vessel-panel-field">
                  <span className="label">Speed</span>
                  <span className="mono">{vessel.speed?.toFixed(1)} kn</span>
                </div>
                <div className="vessel-panel-field">
                  <span className="label">Heading</span>
                  <span className="mono">{vessel.heading}°</span>
                </div>
              </div>
            </div>

            <div className="vessel-panel-section">
              <h4 className="vessel-panel-section-title">Specifications</h4>
              <div className="vessel-panel-grid">
                <div className="vessel-panel-field">
                  <span className="label">Gross Tonnage</span>
                  <span className="mono">{vessel.grossTonnage?.toLocaleString()} GT</span>
                </div>
                <div className="vessel-panel-field">
                  <span className="label">Deadweight</span>
                  <span className="mono">{vessel.deadweight?.toLocaleString()} DWT</span>
                </div>
                <div className="vessel-panel-field">
                  <span className="label">Year Built</span>
                  <span className="mono">{vessel.yearBuilt}</span>
                </div>
                <div className="vessel-panel-field">
                  <span className="label">Length × Beam</span>
                  <span className="mono">{vessel.length}m × {vessel.beam}m</span>
                </div>
              </div>
            </div>

            <div className="vessel-panel-section">
              <h4 className="vessel-panel-section-title">Voyage</h4>
              <div className="vessel-panel-grid">
                <div className="vessel-panel-field">
                  <span className="label">Destination</span>
                  <span>{vessel.destination || '—'}</span>
                </div>
                <div className="vessel-panel-field">
                  <span className="label">ETA</span>
                  <span className="mono">
                    {vessel.eta
                      ? new Date(vessel.eta).toLocaleDateString('en-US', {
                          month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                        })
                      : '—'}
                  </span>
                </div>
                <div className="vessel-panel-field">
                  <span className="label">Last Seen</span>
                  <span>{timeSinceLastSeen()}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'Ownership' && (
          <div className="animate-fadeIn">
            <div className="vessel-panel-section">
              <h4 className="vessel-panel-section-title">Corporate Structure</h4>
              <div className="vessel-panel-ownership-list">
                <div className="vessel-panel-ownership-item">
                  <span className="label">Registered Owner</span>
                  <span className="vessel-panel-ownership-value">
                    {vessel.ownership?.registeredOwner || '—'}
                  </span>
                </div>
                <div className="vessel-panel-ownership-item">
                  <span className="label">Beneficial Owner</span>
                  <span className="vessel-panel-ownership-value">
                    {vessel.ownership?.beneficialOwner || '—'}
                  </span>
                </div>
                <div className="vessel-panel-ownership-item">
                  <span className="label">Operator</span>
                  <span className="vessel-panel-ownership-value">
                    {vessel.ownership?.operator || '—'}
                  </span>
                </div>
              </div>
            </div>

            {vessel.ownership?.flagHistory?.length > 0 && (
              <div className="vessel-panel-section">
                <h4 className="vessel-panel-section-title">Flag History</h4>
                <div className="vessel-panel-flag-history">
                  {vessel.ownership.flagHistory.map((entry, i) => (
                    <div key={i} className="vessel-panel-flag-entry">
                      <span className="vessel-panel-flag-emoji">{entry.flag.emoji}</span>
                      <span>{entry.flag.name}</span>
                      <span className="mono text-muted">{entry.from} — {entry.to}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <OwnershipGraph vessel={vessel} />
          </div>
        )}

        {activeTab === 'Sanctions' && (
          <div className="animate-fadeIn">
            {vessel.sanctions?.matched ? (
              <div className="vessel-panel-section">
                <div className="vessel-panel-sanctions-alert">
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M10 2L18 18H2L10 2Z" fill="var(--danger)" fillOpacity="0.15" stroke="var(--danger)" strokeWidth="1.5"/>
                    <path d="M10 8v4M10 14.5v.5" stroke="var(--danger)" strokeWidth="1.8" strokeLinecap="round"/>
                  </svg>
                  <div>
                    <strong className="text-danger">Sanctions Match Detected</strong>
                    <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                      This vessel has been flagged on {vessel.sanctions.lists.length} sanctions list(s).
                    </p>
                  </div>
                </div>

                {vessel.sanctions.lists.map((item, i) => (
                  <div key={i} className="vessel-panel-sanctions-item">
                    <div className="vessel-panel-sanctions-list-name">{item.name}</div>
                    <div className="vessel-panel-sanctions-meta">
                      <span className="badge badge-danger">{item.matchType}</span>
                      <span className="mono" style={{ color: 'var(--danger)' }}>
                        {Math.round(item.confidence * 100)}% match
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="vessel-panel-section vessel-panel-sanctions-clear">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                  <circle cx="16" cy="16" r="12" stroke="var(--success)" strokeWidth="2" fill="hsla(160, 60%, 45%, 0.1)"/>
                  <path d="M11 16l3.5 3.5L21 12" stroke="var(--success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <span style={{ color: 'var(--success)', fontWeight: 600, fontSize: '0.9375rem' }}>
                  No Sanctions Matches
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                  This vessel has been screened against OFAC, EU, and UN sanctions lists.
                </span>
              </div>
            )}
          </div>
        )}

        {activeTab === 'History' && (
          <div className="animate-fadeIn">
            <div className="vessel-panel-section vessel-panel-history-placeholder">
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none" style={{ opacity: 0.3 }}>
                <circle cx="20" cy="20" r="16" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="4 3"/>
                <path d="M20 12v8l5 3" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span className="text-muted" style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                Port call and movement history
              </span>
              <span className="text-muted" style={{ fontSize: '0.8125rem' }}>
                Connect to backend to view historical AIS data and port calls.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
