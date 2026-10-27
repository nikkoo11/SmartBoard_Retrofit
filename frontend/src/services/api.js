const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
export { API_BASE }

const CSRF_COOKIE_NAME = 'csrftoken'
const CSRF_HEADER_NAME = 'X-CSRFToken'

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

function isDevicePath(path) {
  return String(path || '').startsWith('/device/') || String(path || '').startsWith('device/')
}

async function ensureCsrfCookie() {
  if (getCookie(CSRF_COOKIE_NAME)) return
  const res = await fetch(`${API_BASE}/csrf-token/`, {
    method: 'GET',
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`CSRF acquisition failed: ${res.status}`)
  }
  if (!getCookie(CSRF_COOKIE_NAME)) {
    throw new Error('CSRF cookie unavailable')
  }
}

async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = new Headers(options.headers || {})

  if (options.body instanceof FormData) {
    // let browser set multipart boundary
  } else if (options.body != null && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
    if (typeof options.body !== 'string') {
      options = { ...options, body: JSON.stringify(options.body) }
    }
  }

  const deviceRequest = isDevicePath(path)

  if (UNSAFE_METHODS.has(method) && !deviceRequest) {
    await ensureCsrfCookie()
    const token = getCookie(CSRF_COOKIE_NAME)
    if (token) headers.set(CSRF_HEADER_NAME, token)
  }

  const url = /^https?:\/\//i.test(path) ? path : `${API_BASE}${path}`
  const res = await fetch(url, {
    ...options,
    method,
    headers,
    credentials: 'include',
  })

  if (!res.ok) {
    let message = `API ${res.status}`
    try {
      const data = await res.clone().json()
      if (data && (data.detail || data.message)) message = data.detail || data.message
    } catch (e) {
      try {
        const text = await res.clone().text()
        if (text) message = `${message}: ${text}`
      } catch (e2) {}
    }
    const err = new Error(message)
    err.status = res.status
    throw err
  }

  if (res.status === 204) return null

  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    return res.json()
  }
  if (contentType.includes('application/pdf') || contentType.startsWith('application/octet-stream') || contentType.startsWith('image/')) {
    return res.blob()
  }
  if (contentType.includes('text/')) {
    return res.text()
  }
  try {
    return await res.json()
  } catch (e) {
    return res.blob()
  }
}

export const api = {
  health: () => request('/health/'),
  dashboardSummary: () => request('/dashboard/summary/'),
  cameraStatus: () => request('/camera/status/'),
  records: (params = '') => request(`/records/${params}`),
  record: (id) => request(`/records/${id}/`),
  uploadImage: (formData) => request('/images/upload/', { method: 'POST', body: formData }),
  analytics: (days = 7) => request(`/analytics/?days=${days}`),
  csrfToken: () => request('/csrf-token/'),
  login: ({ username, password }) => request('/auth/login/', { method: 'POST', body: { username, password } }),
  logout: () => request('/auth/logout/', { method: 'POST' }),
  me: () => request('/auth/me/'),
  courses: (search = '') => {
    const query = search ? `?search=${encodeURIComponent(search)}` : ''
    return request(`/courses/${query}`)
  },
  createCourse: (data) => request('/courses/', { method: 'POST', body: data }),
  updateCourse: (id, data) => request(`/courses/${id}/`, { method: 'PATCH', body: data }),
  deleteCourse: (id) => request(`/courses/${id}/`, { method: 'DELETE' }),
  sessions: (params = '') => request(`/sessions/${params}`),
  session: (id) => request(`/sessions/${id}/`),
  createSession: (data) => request('/sessions/', { method: 'POST', body: data }),
  updateSession: (id, data) => request(`/sessions/${id}/`, { method: 'PATCH', body: data }),
  deleteSession: (id) => request(`/sessions/${id}/`, { method: 'DELETE' }),
  generatePdf: (id) => request(`/sessions/${id}/generate-pdf/`, { method: 'POST' }),
  generateCapturePdf: (id) => request(`/captures/${id}/generate-pdf/`, { method: 'POST' }),
  captures: (params = '') => request(`/captures/${params}`),
  createCapture: (formData) => request('/captures/', { method: 'POST', body: formData }),
  capture: (id) => request(`/captures/${id}/`),
  updateCapture: (id, data) => request(`/captures/${id}/`, { method: 'PATCH', body: data }),
  deleteCapture: (id) => request(`/captures/${id}/`, { method: 'DELETE' }),
  ocrCapture: (id, query) => request(`/captures/${id}/ocr/?${query}`, { method: 'POST' }),
  cleanCapture: (id) => request(`/captures/${id}/clean/`, { method: 'POST' }),
  pdfs: (params = '') => request(`/pdfs/${params}`),
  pdf: (id) => request(`/pdfs/${id}/`),
  deletePdf: (id) => request(`/pdfs/${id}/`, { method: 'DELETE' }),
}

export { request }
