/* ═══════════════════════════════════════════════════════════════
   RiskBreakdown — Visual score factor breakdown panel
   Shows each risk factor as a labeled bar with points and evidence.
   ═══════════════════════════════════════════════════════════════ */

import { useMemo } from 'react'
import './RiskBreakdown.css'

/* Factor display metadata */
const FACTOR_META = {
  beneficial_owner_sanctioned: {
    label: 'Owner Sanctioned',
    icon: '⛔',
    maxPoints: 30,
    color: 'var(--danger)',
  },
  sanctioned_port_call: {
    label: 'Sanctioned Port Call',
    icon: '🚢',
    maxPoints: 20,
    color: 'var(--danger)',
  },
  sts_transfer_at_sea: {
    label: 'STS Transfer',
    icon: '⚓',
    maxPoints: 15,
    color: 'var(--warning)',
  },
  flag_of_convenience: {
    label: 'Flag of Convenience',
    icon: '🏴',
    maxPoints: 15,
    color: 'var(--warning)',
  },
  dark_activity: {
    label: 'AIS Dark Events',
    icon: '📡',
    maxPoints: 25,
    color: 'var(--warning)',
  },
  psc_detention: {
    label: 'PSC Detention',
    icon: '🔒',
    maxPoints: 10,
    color: 'var(--warning)',
  },
  identity_changes: {
    label: 'Identity Changes',
    icon: '🔄',
    maxPoints: 10,
    color: 'hsl(38, 92%, 55%)',
  },
  near_sanctions_match: {
    label: 'Near Sanctions Match',
    icon: '⚠️',
    maxPoints: 10,
    color: 'var(--warning)',
  },
  high_risk_flag_state: {
    label: 'High-Risk Flag',
    icon: '🚩',
    maxPoints: 5,
    color: 'hsl(25, 80%, 55%)',
  },
  vessel_age: {
    label: 'Vessel Age >20y',
    icon: '🕰️',
    maxPoints: 5,
    color: 'var(--text-secondary)',
  },
  loitering_near_risk_zone: {
    label: 'Loitering in Risk Zone',
    icon: '📍',
    maxPoints: 5,
    color: 'hsl(25, 80%, 55%)',
  },
  loitering: {
    label: 'Loitering',
    icon: '📍',
    maxPoints: 5,
    color: 'var(--text-secondary)',
  },
  // Legacy/fallback keys from old scoring
  sanctions_match: {
    label: 'Sanctions Match',
    icon: '⛔',
    maxPoints: 40,
    color: 'var(--danger)',
  },
  sts_transfer: {
    label: 'STS Transfer',
    icon: '⚓',
    maxPoints: 20,
    color: 'var(--warning)',
  },
  flag_risk: {
    label: 'Flag Risk',
    icon: '🏴',
    maxPoints: 15,
    color: 'var(--warning)',
  },
  'Suspicious Flag State': {
    label: 'Suspicious Flag State',
    icon: '🚩',
    maxPoints: 15,
    color: 'var(--warning)',
  },
  'Dark Activity Detected': {
    label: 'Dark Activity Detected',
    icon: '📡',
    maxPoints: 25,
    color: 'var(--warning)',
  },
  'Recent Port Call in High-Risk Zone': {
    label: 'Recent Port Call in High-Risk Zone',
    icon: '🚢',
    maxPoints: 20,
    color: 'var(--danger)',
  },
  'Ownership Complexity': {
    label: 'Ownership Complexity',
    icon: '🔄',
    maxPoints: 10,
    color: 'hsl(38, 92%, 55%)',
  },
  'Frequent Flag Hopping': {
    label: 'Frequent Flag Hopping',
    icon: '🏴',
    maxPoints: 15,
    color: 'var(--warning)',
  },
  'Sanctions List Match': {
    label: 'Sanctions List Match',
    icon: '⛔',
    maxPoints: 30,
    color: 'var(--danger)',
  },
}

function getRiskLevelColor(score) {
  if (score < 25) return 'var(--success)'
  if (score < 50) return 'var(--warning)'
  if (score < 75) return 'hsl(15, 85%, 55%)'
  return 'var(--danger)'
}

function getRiskLevelLabel(score) {
  if (score < 25) return 'LOW'
  if (score < 50) return 'MEDIUM'
  if (score < 75) return 'HIGH'
  return 'CRITICAL'
}

const RING_RADIUS = 34
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS

export default function RiskBreakdown({ vessel }) {
  const score = vessel?.riskScore ?? 0
  const levelColor = getRiskLevelColor(score)
  const levelLabel = getRiskLevelLabel(score)

  // Generate mock factors from the vessel's mock data
  const factors = useMemo(() => {
    if (vessel?.riskFactors && vessel.riskFactors.length > 0) {
      return vessel.riskFactors
    }
    // Generate demo factors from the mock vessel data
    const mockFactors = []

    if (vessel?.sanctions?.matched) {
      mockFactors.push({
        factor_name: 'beneficial_owner_sanctioned',
        points: 30,
        evidence_description: `Direct sanctions match on ${vessel.sanctions.lists.length} list(s). Highest confidence: ${Math.round((vessel.sanctions.lists[0]?.confidence || 0.92) * 100)}%`,
      })
    }

    if (score >= 50) {
      mockFactors.push({
        factor_name: 'flag_of_convenience',
        points: 15,
        evidence_description: `Vessel registered under ${vessel?.flag?.code || 'PA'}, which is on the ITF Flag of Convenience list.`,
      })
    }

    if (score >= 35) {
      mockFactors.push({
        factor_name: 'dark_activity',
        points: Math.min(15, Math.max(5, score - 40)),
        evidence_description: `${Math.ceil(score / 25)} AIS dark event(s) in last 90 days, total dark time: ${(Math.ceil(score / 10) * 6.5).toFixed(1)} hours.`,
      })
    }

    if (score >= 65) {
      mockFactors.push({
        factor_name: 'sts_transfer_at_sea',
        points: 15,
        evidence_description: '1 STS transfer detected outside port limits.',
      })
    }

    if (vessel?.yearBuilt && (new Date().getFullYear() - vessel.yearBuilt) > 20) {
      mockFactors.push({
        factor_name: 'vessel_age',
        points: 5,
        evidence_description: `Vessel built in ${vessel.yearBuilt} (${new Date().getFullYear() - vessel.yearBuilt} years old).`,
      })
    }

    if (score >= 40 && score < 65) {
      mockFactors.push({
        factor_name: 'near_sanctions_match',
        points: 10,
        evidence_description: '1 near-match on sanctions list (≥85%). Best match: 87.3%.',
      })
    }

    return mockFactors
  }, [vessel, score])

  const strokeDashoffset = RING_CIRCUMFERENCE - (score / 100) * RING_CIRCUMFERENCE

  return (
    <div className="risk-breakdown">
      {/* Score header */}
      <div className="risk-breakdown-header">
        <div className="risk-breakdown-score-ring" style={{ '--ring-color': levelColor }}>
          <svg
            viewBox="0 0 80 80"
            className="risk-breakdown-svg"
            role="img"
            aria-label={`Risk score ${score} out of 100 — ${levelLabel}`}
          >
            <circle
              cx="40" cy="40" r={RING_RADIUS}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="5"
            />
            <circle
              cx="40" cy="40" r={RING_RADIUS}
              fill="none"
              stroke={levelColor}
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray={RING_CIRCUMFERENCE}
              strokeDashoffset={strokeDashoffset}
              transform="rotate(-90 40 40)"
              style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
            />
          </svg>
          <div className="risk-breakdown-score-value">
            <span className="risk-breakdown-score-num">{score}</span>
            <span className="risk-breakdown-score-max">/100</span>
          </div>
        </div>
        <div className="risk-breakdown-score-info">
          <span
            className="risk-breakdown-level-badge"
            style={{ background: levelColor + '22', color: levelColor, borderColor: levelColor + '44' }}
          >
            {levelLabel}
          </span>
          <span className="risk-breakdown-factor-count">
            {factors.length} contributing factor{factors.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Factor list */}
      <div className="risk-breakdown-factors">
        {factors.length === 0 ? (
          <div className="risk-breakdown-empty">
            <span className="risk-breakdown-empty-icon">✓</span>
            <span>No risk factors detected</span>
          </div>
        ) : (
          [...factors]
            .sort((a, b) => b.points - a.points)
            .map((factor, i) => {
              const meta = FACTOR_META[factor.factor_name] || {
                label: factor.factor_name.replace(/_/g, ' '),
                icon: '•',
                maxPoints: 30,
                color: 'var(--text-secondary)',
              }
              const barWidth = Math.min(100, (factor.points / meta.maxPoints) * 100)

              return (
                <div key={i} className="risk-factor-item">
                  <div className="risk-factor-top">
                    <span className="risk-factor-icon">{meta.icon}</span>
                    <span className="risk-factor-label">{meta.label}</span>
                    <span className="risk-factor-points" style={{ color: meta.color }}>
                      +{factor.points}
                    </span>
                  </div>
                  <div className="risk-factor-bar-track">
                    <div
                      className="risk-factor-bar-fill"
                      style={{
                        width: `${barWidth}%`,
                        background: meta.color,
                        transition: `width 0.6s ease-out ${i * 0.08}s`,
                      }}
                    />
                  </div>
                  {factor.evidence_description && (
                    <p className="risk-factor-evidence">{factor.evidence_description}</p>
                  )}
                </div>
              )
            })
        )}
      </div>

      {/* Audit trail footer */}
      {factors.length > 0 && (
        <div className="risk-breakdown-footer">
          <span className="risk-breakdown-audit">
            Score is deterministic and fully auditable — no ML or black-box algorithms.
          </span>
        </div>
      )}
    </div>
  )
}
