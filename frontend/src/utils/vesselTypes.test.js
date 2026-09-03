import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  VESSEL_TYPES,
  getVesselColor,
  getVesselColorVar,
  getVesselLabel,
  getVesselBadgeClass,
  mapShipTypeCodeToCategory,
} from './vesselTypes.js'

test('getVesselColor returns correct color or fallback', () => {
  assert.equal(getVesselColor('cargo'), VESSEL_TYPES.cargo.color)
  assert.equal(getVesselColor('tanker'), VESSEL_TYPES.tanker.color)
  assert.equal(getVesselColor('unknown_type'), VESSEL_TYPES.other.color)
})

test('getVesselColorVar returns correct CSS variable or fallback', () => {
  assert.equal(getVesselColorVar('cargo'), VESSEL_TYPES.cargo.colorVar)
  assert.equal(getVesselColorVar('tanker'), VESSEL_TYPES.tanker.colorVar)
  assert.equal(getVesselColorVar('unknown_type'), VESSEL_TYPES.other.colorVar)
})

test('getVesselLabel returns human-readable label', () => {
  assert.equal(getVesselLabel('cargo'), 'Cargo')
  assert.equal(getVesselLabel('tanker'), 'Tanker')
  assert.equal(getVesselLabel('other'), 'Other')
})

test('getVesselBadgeClass returns CSS class', () => {
  assert.equal(getVesselBadgeClass('cargo'), 'badge-accent')
  assert.equal(getVesselBadgeClass('tanker'), 'badge-warning')
})

test('mapShipTypeCodeToCategory maps ITU AIS codes correctly', () => {
  assert.equal(mapShipTypeCodeToCategory(30), 'fishing')
  assert.equal(mapShipTypeCodeToCategory(35), 'military')
  assert.equal(mapShipTypeCodeToCategory(60), 'passenger')
  assert.equal(mapShipTypeCodeToCategory(70), 'cargo')
  assert.equal(mapShipTypeCodeToCategory(85), 'tanker')
  assert.equal(mapShipTypeCodeToCategory(99), 'other')
  assert.equal(mapShipTypeCodeToCategory('invalid'), 'other')
})

