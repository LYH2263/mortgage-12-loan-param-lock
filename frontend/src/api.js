async function request(path, options) {
  const r = await fetch(path, options)
  if (!r.ok) {
    let msg = await r.text()
    try { msg = JSON.parse(msg).detail ?? msg } catch { /* keep raw body */ }
    throw new Error(msg)
  }
  if (r.status === 204) return null
  return r.json()
}
export function getJSON(path) { return request(path) }
export function postJSON(path, body) {
  return request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
export function patchJSON(path, body) {
  return request(path, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}
