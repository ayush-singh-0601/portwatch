import { useState } from 'react'
import { getVesselColor, getVesselLabel } from '../../utils/vesselTypes'
import { copyToClipboard } from '../../utils/clipboard'
import './IdentityCard.css'

/**
 * Card showing vessel identity — IMO, MMSI, call sign, flag, type with dot indicator.
 */
export default function IdentityCard({ vessel }) {
  const [copiedField, setCopiedField] = useState(null)

  if (!vessel) return null

  const typeColor = getVesselColor(vessel.type)

  const handleCopy = async (field, value) => {
    if (!value) return
    const ok = await copyToClipboard(value)
    if (ok) {
      setCopiedField(field)
      setTimeout(() => setCopiedField(null), 2000)
    }
  }

  return (
    <div className="identity-card">
      <h4 className="vessel-panel-section-title">Identity</h4>

      <div className="identity-card-grid">
        <div
          className="identity-card-item identity-card-copyable"
          onClick={() => handleCopy('imo', vessel.imo)}
          title="Click to copy IMO"
        >
          <span className="label">IMO Number</span>
          <span className="mono identity-card-value">
            {vessel.imo || '—'}
            {copiedField === 'imo' && <span className="identity-card-copied">Copied!</span>}
          </span>
        </div>
        <div
          className="identity-card-item identity-card-copyable"
          onClick={() => handleCopy('mmsi', vessel.mmsi)}
          title="Click to copy MMSI"
        >
          <span className="label">MMSI</span>
          <span className="mono identity-card-value">
            {vessel.mmsi || '—'}
            {copiedField === 'mmsi' && <span className="identity-card-copied">Copied!</span>}
          </span>
        </div>
        <div className="identity-card-item">
          <span className="label">Call Sign</span>
          <span className="mono identity-card-value">{vessel.callSign || '—'}</span>
        </div>
        <div className="identity-card-item">
          <span className="label">Flag State</span>
          <span className="identity-card-value identity-card-flag">
            <span style={{ fontSize: '1.1rem' }}>{vessel.flag?.emoji ?? '🏳️'}</span>
            {vessel.flag?.name ?? 'Unknown'}
          </span>
        </div>
        <div className="identity-card-item identity-card-item-full">
          <span className="label">Vessel Type</span>
          <span className="identity-card-value identity-card-type">
            <span
              className="identity-card-type-dot"
              style={{ background: typeColor, boxShadow: `0 0 6px ${typeColor}44` }}
            />
            {getVesselLabel(vessel.type)}
          </span>
        </div>
        {vessel.yearBuilt && (
          <div className="identity-card-item">
            <span className="label">Year Built</span>
            <span className="mono identity-card-value">{vessel.yearBuilt}</span>
          </div>
        )}
        {vessel.grossTonnage && (
          <div className="identity-card-item">
            <span className="label">Gross Tonnage</span>
            <span className="mono identity-card-value">{Number(vessel.grossTonnage).toLocaleString()} GT</span>
          </div>
        )}
      </div>
    </div>
  )
}
