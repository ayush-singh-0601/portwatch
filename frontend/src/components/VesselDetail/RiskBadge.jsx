import { getRiskColor, getRiskLabel } from '../../utils/riskColors'
import './RiskBadge.css'

/**
 * Circular risk score badge with SVG arc and animated glow.
 * @param {{ score: number, size?: number }} props
 */
export default function RiskBadge({ score = 0, size = 72 }) {
  const safeNum = Number(score)
  const clampedScore = Number.isFinite(safeNum) ? Math.max(0, Math.min(100, Math.round(safeNum))) : 0
  const color = getRiskColor(clampedScore)
  const label = getRiskLabel(clampedScore)
  const isHigh = clampedScore > 60

  // SVG circular progress
  const center = size / 2
  const strokeWidth = size > 60 ? 4 : 3
  const radius = center - strokeWidth - 2
  const circumference = 2 * Math.PI * radius
  const dashOffset = circumference - (clampedScore / 100) * circumference

  return (
    <div
      className={`risk-badge ${isHigh ? 'risk-badge-high' : ''}`}
      style={{ width: size, height: size }}
      title={label}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="risk-badge-svg"
      >
        {/* Background ring */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className="risk-badge-arc"
          style={{
            transform: 'rotate(-90deg)',
            transformOrigin: 'center',
            filter: `drop-shadow(0 0 4px ${color})`,
          }}
        />
        {/* Glow circle for high risk */}
        {isHigh && (
          <circle
            cx={center}
            cy={center}
            r={radius + 4}
            fill="none"
            stroke={color}
            strokeWidth="1"
            opacity="0.2"
            className="risk-badge-glow-ring"
          />
        )}
      </svg>

      <div className="risk-badge-content">
        <span
          className="risk-badge-score mono"
          style={{ color, fontSize: size > 60 ? '1.25rem' : '0.875rem' }}
        >
          {clampedScore}
        </span>
        {size > 60 && (
          <span
            className="risk-badge-label"
            style={{ color, fontSize: '0.5rem' }}
          >
            {label.split(' ')[0]}
          </span>
        )}
      </div>
    </div>
  )
}
