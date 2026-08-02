/**
 * DRF returns a bare array when pagination is off and a `{results: []}`
 * envelope when it kicks in. Callers should not have to care which.
 */
export function unwrapList(data) {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}
