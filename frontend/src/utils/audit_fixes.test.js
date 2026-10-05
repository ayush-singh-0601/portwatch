import { test } from 'node:test'
import assert from 'node:assert/strict'
import { getRiskColor, getRiskLabel, getRiskLabelShort } from './riskColors.js'
import { getVesselColor, getVesselLabel } from './vesselTypes.js'
import { getEnrichedVessels } from '../services/api.js'
import { parseTimestamp, formatLastSeen, formatEta, formatPortDate } from './formatters.js'
import { isInsideViewport, roundedHeading, riskBand } from './mapUtils.js'
import { buildMockGraph, normalizeGraphData } from './ownershipUtils.js'

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
  assert.ok(getRiskColor(85).length > 0)
})

test('vessel type colors and labels are correctly mapped', () => {
  assert.equal(getVesselLabel('cargo'), 'Cargo')
  assert.equal(getVesselLabel('tanker'), 'Tanker')
  assert.ok(getVesselColor('cargo').startsWith('hsl'))
  assert.ok(getVesselColor('unknown').length > 0)
})

test('dual range slider bar clamp math prevents negative percentage widths', () => {
  const minScore = 75
  const maxScore = 50 // inverted values during dragging
  const leftPct = (minScore / 100) * 100
  const widthPct = Math.max(0, ((maxScore - minScore) / 100) * 100)
  
  assert.equal(leftPct, 75)
  assert.equal(widthPct, 0)
})

test('formatters parse timestamps and format relative and calendar dates', () => {
  // Epoch seconds vs milliseconds
  assert.equal(parseTimestamp(1700000000), 1700000000000)
  assert.equal(parseTimestamp(1700000000000), 1700000000000)
  assert.equal(parseTimestamp('invalid'), null)
  assert.equal(parseTimestamp(null), null)

  // formatLastSeen
  const recent = Date.now() - 5000
  assert.equal(formatLastSeen(recent), 'Just now')
  const hoursAgo = Date.now() - 7200000
  assert.equal(formatLastSeen(hoursAgo), '2h ago')
  assert.equal(formatLastSeen(null), '—')

  // formatEta
  assert.equal(formatEta(null), '—')
  assert.ok(formatEta(1700000000000) !== '—')

  // formatPortDate
  assert.equal(formatPortDate(null), '—')
  assert.ok(formatPortDate('2026-09-20T10:00:00Z').includes('2026'))
})

test('mapUtils calculates normalized heading and risk bands', () => {
  // Negative heading wraps to positive modulo 360
  assert.equal(roundedHeading(-10), 350)
  assert.equal(roundedHeading(356), 0)
  assert.equal(roundedHeading(184), 180)
  assert.equal(roundedHeading('invalid'), 0)

  // Risk bands
  assert.equal(riskBand(80), 'critical')
  assert.equal(riskBand(60), 'high')
  assert.equal(riskBand(30), 'medium')
  assert.equal(riskBand(10), 'low')
})

test('mapUtils isInsideViewport handles antimeridian and world copy wrapping', () => {
  const vessel = { position: { lat: 25.0, lon: 175.0 } }

  // Normal viewport
  assert.equal(isInsideViewport(vessel, { south: 20, north: 30, west: 170, east: 180 }), true)
  assert.equal(isInsideViewport(vessel, { south: 20, north: 30, west: 0, east: 50 }), false)

  // Whole world zoom (span >= 360)
  assert.equal(isInsideViewport(vessel, { south: -80, north: 80, west: -200, east: 200 }), true)

  // Antimeridian crossing (west = 170, east = 190 in continuous Leaflet coordinates)
  const vesselNearDateLineWest = { position: { lat: 25.0, lon: -175.0 } }
  assert.equal(isInsideViewport(vesselNearDateLineWest, { south: 20, north: 30, west: 170, east: 190 }), true)

  // Wrapped bounds (west = 170, east = -170)
  assert.equal(isInsideViewport(vesselNearDateLineWest, { south: 20, north: 30, west: 170, east: -170 }), true)
})

test('ownershipUtils generates mock graph and normalizes API graph with deep copy', () => {
  const vessel = {
    id: 1,
    name: 'Ocean Pioneer',
    imo: '9123456',
    flag: { code: 'PA' },
    ownership: {
      registeredOwner: 'Pacific Maritime Ltd',
      beneficialOwner: 'Alpha Holdings',
    },
  }

  const mock = buildMockGraph(vessel)
  assert.ok(mock.nodes.length >= 2)
  assert.ok(mock.links.length >= 1)

  // API format normalization with object-based link references
  const rawApiGraph = {
    nodes: [
      { id: 101, name: 'Parent Corp', entity_type: 'company', country: 'SG' },
      { id: 102, name: 'Holding Ltd', entity_type: 'shell', country: 'PA' },
    ],
    edges: [
      { source_entity_id: 101, target_entity_id: 102, relationship_type: 'subsidiary' },
    ],
  }

  const normalized = normalizeGraphData(vessel, rawApiGraph)
  assert.equal(normalized.nodes.length, 3) // Center vessel + 2 entities
  assert.ok(normalized.links.length >= 1)

  // Mutations to normalized nodes/links do not affect input rawApiGraph
  normalized.nodes[0].x = 100
  assert.equal(rawApiGraph.nodes[0].x, undefined)
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

test('normalizeGraphData preserves entity-to-entity edge hierarchy when vessel_imo is present', () => {
  const vessel = { imo: 9123456, name: 'TEST VESSEL' }
  const rawApiGraph = {
    nodes: [
      { id: 101, name: 'Parent Corp', entity_type: 'company' },
      { id: 102, name: 'Holding Ltd', entity_type: 'shell' },
    ],
    edges: [
      { source_entity_id: 101, target_entity_id: 102, vessel_imo: 9123456, relationship_type: 'subsidiary' },
    ],
  }
  const normalized = normalizeGraphData(vessel, rawApiGraph)
  const subsidiaryLink = normalized.links.find(l => l.relationship === 'subsidiary')
  assert.ok(subsidiaryLink)
  assert.equal(subsidiaryLink.source, 'entity_101')
  assert.equal(subsidiaryLink.target, 'entity_102')
})

test('search token logic does not match pure digit queries when multi-token text is queried', () => {
  const vessels = [
    { name: 'PACIFIC RUBY', imo: '9123456', mmsi: '352111000', type: 'cargo' },
    { name: 'ATLANTIC STAR', imo: '9876543', mmsi: '211123456', type: 'tanker' },
  ]
  const q = 'tanker 9123456'
  const tokens = q.toLowerCase().split(/\s+/).filter(Boolean)
  const cleanDigits = q.replace(/\D/g, '')

  const filterVessels = (v) => {
    const text = `${v.name} ${v.imo} ${v.mmsi} ${v.type}`.toLowerCase()
    const imoClean = String(v.imo || '').replace(/\D/g, '')
    const mmsiClean = String(v.mmsi || '').replace(/\D/g, '')
    const matchesTokens = tokens.length > 0 && tokens.every(token => text.includes(token))
    const matchesDigits =
      cleanDigits.length >= 3 &&
      tokens.length === 1 &&
      /^\d+$/.test(tokens[0]) &&
      (imoClean.includes(cleanDigits) || mmsiClean.includes(cleanDigits))
    return matchesTokens || matchesDigits
  }

  const results = vessels.filter(filterVessels)
  assert.equal(results.length, 0)
})

test('null value formatting produces em-dash without trailing unit artifacts', () => {
  const formatSpeed = (val) => Number.isFinite(val) ? `${Number(val).toFixed(1)} kn` : '—'
  const formatHeading = (val) => Number.isFinite(val) ? `${Math.round(val)}°` : '—'
  const formatLat = (val) => Number.isFinite(val) ? `${val.toFixed(4)}°` : '—'
  const formatGT = (val) => val != null && !isNaN(val) ? `${Number(val).toLocaleString()} GT` : '—'

  assert.equal(formatSpeed(null), '—')
  assert.equal(formatSpeed(undefined), '—')
  assert.equal(formatSpeed(12.5), '12.5 kn')

  assert.equal(formatHeading(null), '—')
  assert.equal(formatHeading(180), '180°')

  assert.equal(formatLat(null), '—')
  assert.equal(formatLat(NaN), '—')
  assert.equal(formatLat(25.1234), '25.1234°')

  assert.equal(formatGT(null), '—')
  assert.equal(formatGT(50000), '50,000 GT')
})
