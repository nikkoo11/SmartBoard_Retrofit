import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Overview.vue'
import Courses from '../views/Courses.vue'
import LessonSessions from '../views/LessonSessions.vue'
import WhiteboardCapture from '../views/WhiteboardCapture.vue'
import PdfArchive from '../views/PdfArchive.vue'
import AiAssistant from '../views/AiAssistant.vue'
import Settings from '../views/Settings.vue'
import HelpSupport from '../views/HelpSupport.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: Dashboard },
  { path: '/courses', component: Courses },
  { path: '/sessions', component: LessonSessions },
  { path: '/capture', component: WhiteboardCapture },
  { path: '/archive', component: PdfArchive },
  { path: '/assistant', component: AiAssistant },
  { path: '/settings', component: Settings },
  { path: '/help', component: HelpSupport },
]

export default createRouter({ history: createWebHistory(), routes })
