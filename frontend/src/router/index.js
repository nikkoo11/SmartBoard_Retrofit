import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Overview.vue'
import Login from '../views/Login.vue'
import Courses from '../views/Courses.vue'
import LessonSessions from '../views/LessonSessions.vue'
import SessionDetail from '../views/SessionDetail.vue'
import WhiteboardCapture from '../views/WhiteboardCapture.vue'
import PdfArchive from '../views/PdfArchive.vue'
import AiAssistant from '../views/AiAssistant.vue'
import Settings from '../views/Settings.vue'
import HelpSupport from '../views/HelpSupport.vue'
import { useAuth } from '../composables/useAuth.js'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', component: Login },
  { path: '/dashboard', component: Dashboard },
  { path: '/courses', component: Courses },
  { path: '/sessions', component: LessonSessions },
  { path: '/sessions/:id', component: SessionDetail },
  { path: '/capture', component: WhiteboardCapture },
  { path: '/archive', component: PdfArchive },
  { path: '/assistant', component: AiAssistant },
  { path: '/settings', component: Settings },
  { path: '/help', component: HelpSupport },
]

const router = createRouter({ history: createWebHistory(), routes })

let hydrationPromise = null
function ensureHydrated() {
  const { hydrate } = useAuth()
  if (!hydrationPromise) {
    hydrationPromise = hydrate().catch(() => null)
  }
  return hydrationPromise
}

function isInternalRedirect(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') && value !== '/login'
}

router.beforeEach(async (to) => {
  await ensureHydrated()
  const { isAuthenticated } = useAuth()

  if (to.path === '/login') {
    if (isAuthenticated.value) {
      const redirect = to.query.redirect
      return isInternalRedirect(redirect) ? redirect : '/dashboard'
    }
    return true
  }

  if (!isAuthenticated.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  return true
})

router.onError((err) => {
  console.error('[SmartBoard] router error', err)
  const msg = String(err && err.message ? err.message : err)
  const isImportError = /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed/i.test(msg)
  if (isImportError) {
    try {
      if (sessionStorage.getItem('smartboard_reload_attempted') === '1') return
      sessionStorage.setItem('smartboard_reload_attempted', '1')
    } catch (e) {}
    window.location.reload()
  }
})

router.afterEach(() => {
  try { sessionStorage.removeItem('smartboard_reload_attempted') } catch (e) {}
})

export default router
