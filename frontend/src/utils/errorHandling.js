/**
 * Utility functions for error normalization and error boundary support.
 */

export function normalizeError(error) {
  if (!error) return { message: 'An unknown error occurred', name: 'UnknownError' }
  if (typeof error === 'string') return { message: error, name: 'Error' }
  return {
    message: error.message || String(error),
    name: error.name || 'Error',
    stack: error.stack,
  }
}

export function formatErrorMessage(error) {
  const norm = normalizeError(error)
  return `${norm.name}: ${norm.message}`
}
