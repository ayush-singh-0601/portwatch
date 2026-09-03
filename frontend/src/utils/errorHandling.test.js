import { test } from 'node:test'
import assert from 'node:assert/strict'
import { normalizeError, formatErrorMessage } from './errorHandling.js'

test('normalizeError handles string errors', () => {
  const res = normalizeError('Failed to fetch')
  assert.equal(res.message, 'Failed to fetch')
  assert.equal(res.name, 'Error')
})

test('normalizeError handles Error instances', () => {
  const err = new TypeError('Invalid coordinate')
  const res = normalizeError(err)
  assert.equal(res.message, 'Invalid coordinate')
  assert.equal(res.name, 'TypeError')
})

test('normalizeError handles null/undefined errors', () => {
  const res = normalizeError(null)
  assert.equal(res.message, 'An unknown error occurred')
})

test('formatErrorMessage formats string output', () => {
  const formatted = formatErrorMessage(new Error('Network timeout'))
  assert.equal(formatted, 'Error: Network timeout')
})
