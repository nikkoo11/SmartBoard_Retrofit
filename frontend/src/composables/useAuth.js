import { ref, computed } from 'vue'
import { api } from '../services/api.js'

const user = ref(null)
const loading = ref(false)
const error = ref(null)

let inFlight = null

function clearUser() {
  user.value = null
}

function isAuthError(err) {
  const status = err && (err.status || err.response?.status)
  if (status === 401 || status === 403) return true
  const message = err && err.message ? err.message : ''
  return /API (401|403)/.test(message)
}

async function run(task) {
  if (loading.value) {
    if (inFlight) return inFlight
  }
  loading.value = true
  error.value = null
  inFlight = (async () => {
    try {
      return await task()
    } finally {
      loading.value = false
      inFlight = null
    }
  })()
  return inFlight
}

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(user.value && user.value.id))

  async function login(username, password) {
    return run(async () => {
      try {
        const data = await api.login({ username, password })
        user.value = (data && data.user) ? data.user : null
        error.value = null
        return data
      } catch (e) {
        clearUser()
        error.value = e && e.message ? e.message : 'Login failed.'
        throw e
      }
    })
  }

  async function logout() {
    return run(async () => {
      let serverError = null
      try {
        await api.logout()
      } catch (e) {
        serverError = e
      }
      clearUser()
      if (serverError) {
        error.value = serverError.message || 'Logout failed.'
        throw serverError
      }
      error.value = null
      return { logged_out: true }
    })
  }

  async function hydrate() {
    return run(async () => {
      try {
        const data = await api.me()
        user.value = data ? { id: data.id, username: data.username, display_name: data.display_name } : null
        error.value = null
        return data
      } catch (e) {
        if (isAuthError(e)) {
          clearUser()
          error.value = null
          return null
        }
        error.value = e && e.message ? e.message : 'Session check failed.'
        throw e
      }
    })
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    login,
    logout,
    hydrate,
  }
}
