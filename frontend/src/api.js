export async function getJSON(path) {
  const r = await fetch(path)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
async function sendJSON(method, path, body) {
  const r = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
export const postJSON = (path, body) => sendJSON('POST', path, body)
export const patchJSON = (path, body) => sendJSON('PATCH', path, body)

export function errMsg(raw) {
  const text = raw && raw.message ? raw.message : String(raw)
  try {
    const body = JSON.parse(text)
    const detail = body.detail
    if (detail && typeof detail === 'object') return detail.message || JSON.stringify(detail)
    return typeof detail === 'string' ? detail : text
  } catch {
    return text
  }
}
