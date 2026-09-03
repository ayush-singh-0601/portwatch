import { test } from 'node:test'
import assert from 'node:assert/strict'
import { getApiErrorMessage } from './api.js'

test('getApiErrorMessage extracts detail string', () => {
  const err = { response: { data: { detail: 'Vessel not found' } } }
  assert.equal(getApiErrorMessage(err), 'Vessel not found')
})

test('getApiErrorMessage extracts detail array error message', () => {
  const err = { response: { data: { detail: [{ msg: 'Invalid coordinates' }] } } }
  assert.equal(getApiErrorMessage(err), 'Invalid coordinates')
})

test('getApiErrorMessage extracts message property', () => {
  const err = { response: { data: { message: 'Internal server error' } } }
  assert.equal(getApiErrorMessage(err), 'Internal server error')
})

test('getApiErrorMessage handles string error input', () => {
  assert.equal(getApiErrorMessage('Custom error string'), 'Custom error string')
})

test('getApiErrorMessage handles null or undefined error', () => {
  assert.equal(getApiErrorMessage(null), 'An unexpected error occurred')
})
