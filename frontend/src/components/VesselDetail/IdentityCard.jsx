import { getVesselColor, getVesselLabel } from '../../utils/vesselTypes'
import './IdentityCard.css'

/**
 * Card showing vessel identity — IMO, MMSI, call sign, flag, type with dot indicator.
 */
export default function IdentityCard({ vessel }) {
  if (!vessel) return null

  const typeColor = getVesselColor(vessel.type)

  return (
    <div className="identity-card">
      <h4 className="vessel-panel-section-title">Identity</h4>

      <div className="identity-card-grid">
        <div className="identity-card-item">
          <span className="label">IMO Number</span>
          <span className="mono identity-card-value">{vessel.imo}</span>
        </div>
        <div className="identity-card-item">
          <span className="label">MMSI</span>
          <span className="mono identity-card-value">{vessel.mmsi}</span>
        </div>
        <div className="identity-card-item">
          <span className="label">Call Sign</span>
          <span className="mono identity-card-value">{vessel.callSign}</span>
        </div>
        <div className="identity-card-item">
          <span className="label">Flag State</span>
          <span className="identity-card-value identity-card-flag">
            <span style={{ fontSize: '1.1rem' }}>{vessel.flag?.emoji}</span>
            {vessel.flag?.name}
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
      </div>
    </div>
  )
}
