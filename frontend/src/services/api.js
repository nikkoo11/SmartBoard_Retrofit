const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) throw new Error(`API ${res.status}`)
  return res.json()
}

export const api = {
  health: () => request('/health/'),
  dashboardSummary: () => request('/dashboard/summary/'),
  cameraStatus: () => request('/camera/status/'),
  records: (params = '') => request(`/records/${params}`),
  record: (id) => request(`/records/${id}/`),
  uploadImage: (formData) => request('/images/upload/', { method: 'POST', body: formData }),
  analytics: (days = 7) => request(`/analytics/?days=${days}`),
}
