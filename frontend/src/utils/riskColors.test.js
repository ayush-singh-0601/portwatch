import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  getRiskColor,
  getRiskColorVar,
  getRiskLabel,
  getRiskLabelShort,
  getRiskGlow,
} from './riskColors.js'

test('getRiskColor returns appropriate HSL string', () => {
  assert.equal(getRiskColor(15), 'hsl(160, 60%, 45%)')
  assert.equal(getRiskColor(45), 'hsl(38, 92%, 55%)')
  assert.equal(getRiskColor(75), 'hsl(0, 85%, 55%)')
  assert.equal(getRiskColor(90), 'hsl(0, 85%, 55%)')
  // Boundary tests
  assert.equal(getRiskColor(0), 'hsl(160, 60%, 45%)')
  assert.equal(getRiskColor(30), 'hsl(160, 60%, 45%)')
  assert.equal(getRiskColor(31), 'hsl(38, 92%, 55%)')
  assert.equal(getRiskColor(60), 'hsl(38, 92%, 55%)')
  assert.equal(getRiskColor(61), 'hsl(0, 85%, 55%)')
})

test('getRiskLabel returns correct classification', () => {
  assert.equal(getRiskLabel(0), 'LOW RISK')
  assert.equal(getRiskLabel(30), 'LOW RISK')
  assert.equal(getRiskLabel(50), 'MEDIUM RISK')
  assert.equal(getRiskLabel(60), 'MEDIUM RISK')
  assert.equal(getRiskLabel(75), 'HIGH RISK')
  assert.equal(getRiskLabel(100), 'HIGH RISK')
})

test('getRiskLabelShort returns abbreviation', () => {
  assert.equal(getRiskLabelShort(20), 'LOW')
  assert.equal(getRiskLabelShort(40), 'MED')
  assert.equal(getRiskLabelShort(70), 'HIGH')
})

test('getRiskColorVar returns CSS variable', () => {
  assert.equal(getRiskColorVar(10), 'var(--success)')
  assert.equal(getRiskColorVar(50), 'var(--warning)')
  assert.equal(getRiskColorVar(90), 'var(--danger)')
})

test('getRiskGlow returns shadow string', () => {
  assert.ok(getRiskGlow(10).includes('hsla(160'))
  assert.ok(getRiskGlow(50).includes('hsla(38'))
  assert.ok(getRiskGlow(90).includes('hsla(0'))
})

test('getRiskGradient and getRiskBadgeClass return correct tier styles', async () => {
  const { getRiskGradient, getRiskBadgeClass } = await import('./riskColors.js')
  assert.equal(getRiskBadgeClass(15), 'badge-success')
  assert.equal(getRiskBadgeClass(45), 'badge-warning')
  assert.equal(getRiskBadgeClass(85), 'badge-danger')
  assert.ok(getRiskGradient(15).includes('linear-gradient'))
})


