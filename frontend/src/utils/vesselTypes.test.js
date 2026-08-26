import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  VESSEL_TYPES,
  getVesselColor,
  getVesselColorVar,
  getVesselLabel,
  getVesselBadgeClass,
} from './vesselTypes.js'

test('getVesselColor returns correct color or fallback', () => {
  assert.equal(getVesselColor('cargo'), VESSEL_TYPES.cargo.color)
  assert.equal(getVesselColor('tanker'), VESSEL_TYPES.tanker.color)
  assert.equal(getVesselColor('unknown_type'), VESSEL_TYPES.other.color)
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
