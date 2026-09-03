import { test } from 'node:test'
import assert from 'node:assert/strict'
import { copyToClipboard } from './clipboard.js'

test('copyToClipboard returns false for empty input', async () => {
  const res1 = await copyToClipboard('')
  assert.equal(res1, false)

  const res2 = await copyToClipboard(null)
  assert.equal(res2, false)
})

test('copyToClipboard handles non-browser environment safely', async () => {
  const res = await copyToClipboard('9123456')
  // In pure node environment without window/document, safely returns false without crashing
  assert.equal(typeof res, 'boolean')
})
