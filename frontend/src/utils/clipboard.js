/**
 * Safe clipboard copy utility with fallback for non-secure contexts.
 */

export async function copyToClipboard(text) {
  if (!text) return false
  try {
    if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(String(text))
      return true
    }
  } catch (err) {
    console.warn('[Clipboard] Failed to copy using navigator.clipboard:', err)
  }

  // Fallback for non-secure / mock environments
  try {
    if (typeof document !== 'undefined') {
      const textarea = document.createElement('textarea')
      textarea.value = String(text)
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)
      return success
    }
  } catch (err) {
    console.warn('[Clipboard] Fallback execCommand failed:', err)
  }

  return false
}
