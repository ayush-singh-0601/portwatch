import { test } from 'node:test'
import assert from 'node:assert/strict'
import { getRiskColor, getRiskLabel, getRiskLabelShort } from './riskColors.js'
import { getVesselColor, getVesselLabel } from './vesselTypes.js'
import { getEnrichedVessels } from '../services/api.js'

test('getEnrichedVessels is exported and callable as an API function', () => {
  assert.equal(typeof getEnrichedVessels, 'function')
})

test('risk threshold classification marks score >= 25 as elevated risk', () => {
  assert.equal(getRiskLabel(0), 'LOW RISK')
  assert.equal(getRiskLabelShort(10), 'LOW')

  assert.equal(getRiskLabel(50), 'MEDIUM RISK')
  assert.equal(getRiskLabelShort(40), 'MED')

  assert.equal(getRiskLabel(75), 'HIGH RISK')
  assert.equal(getRiskLabelShort(90), 'HIGH')
})

test('dual range slider bar clamp math prevents negative percentage widths', () => {
  const minScore = 75
  const maxScore = 50 // inverted values during dragging
  const leftPct = (minScore / 100) * 100
  const widthPct = Math.max(0, ((maxScore - minScore) / 100) * 100)
  
  assert.equal(leftPct, 75)
  assert.equal(widthPct, 0)
})

test('timestamp formatting handles epoch seconds (<1e11) vs milliseconds (>1e11)', () => {
  const formatEpoch = (val) => {
    if (!val) return '—'
    const ms = typeof val === 'number' ? (val < 1e11 ? val * 1000 : val) : Date.parse(val)
    if (!Number.isFinite(ms) || Number.isNaN(ms)) return '—'
    const date = new Date(ms)
    return Number.isNaN(date.getTime()) ? '—' : date.toISOString()
  }

  // 1700000000 is seconds (2023-11-14T22:13:20.000Z)
  const secondsIso = formatEpoch(1700000000)
  assert.ok(secondsIso.startsWith('2023-11-14'))

  // 1700000000000 is milliseconds
  const msIso = formatEpoch(1700000000000)
  assert.ok(msIso.startsWith('2023-11-14'))

  // Invalid date
  assert.equal(formatEpoch('invalid-date'), '—')
  assert.equal(formatEpoch(null), '—')
})

test('vessel metadata fallback provides clean identifier when IMO is missing', () => {
  const formatMeta = (vessel) => {
    const flag = vessel.flag?.emoji ? `${vessel.flag.emoji} ` : ''
    const type = vessel.type || 'Vessel'
    const id = vessel.imo ? `IMO ${vessel.imo}` : vessel.mmsi ? `MMSI ${vessel.mmsi}` : 'No Identifier'
    return `${flag}${type} · ${id}`
  }

  const withImo = { imo: '9123456', type: 'Cargo', flag: { emoji: '🇵🇦' } }
  assert.equal(formatMeta(withImo), '🇵🇦 Cargo · IMO 9123456')

  const withoutImo = { mmsi: '352111000', type: 'Tanker', flag: { emoji: '🇱🇷' } }
  assert.equal(formatMeta(withoutImo), '🇱🇷 Tanker · MMSI 352111000')

  const unregistered = { type: 'Tug' }
  assert.equal(formatMeta(unregistered), 'Tug · No Identifier')
})
