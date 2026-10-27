<script setup>
import { ref, onMounted } from 'vue'
import { BookOpen, Calendar, Image, FileText } from 'lucide-vue-next'
import { api, request } from '../services/api.js'

const courseCount  = ref(0)
const sessionCount = ref(0)
const captureCount = ref(0)
const pdfCount     = ref(0)
const statusCounts = ref({ draft: 0, capturing: 0, processing: 0, finalized: 0 })
const recentSessions = ref([])
const recentPdfs     = ref([])
const loading = ref(false)
const error   = ref('')

async function getCount(path) {
  try {
    const data = await request(path)
    if (typeof data.count === 'number') return data.count
    if (Array.isArray(data)) return data.length
    if (Array.isArray(data.results)) return data.results.length
    return 0
  } catch { return 0 }
}

async function fetchList(path) {
  try {
    const data = await request(path)
    if (Array.isArray(data)) return data
    if (Array.isArray(data.results)) return data.results
    return []
  } catch { return [] }
}

onMounted(async () => {
  loading.value = true
  error.value   = ''
  try {
    const [cCount, sCount, capCount, pCount, sDraft, sCapt, sProc, sFin, sessions, pdfs] = await Promise.all([
      getCount('/courses/'),
      getCount('/sessions/'),
      getCount('/captures/'),
      getCount('/pdfs/'),
      getCount('/sessions/?status=draft'),
      getCount('/sessions/?status=capturing'),
      getCount('/sessions/?status=processing'),
      getCount('/sessions/?status=finalized'),
      fetchList('/sessions/'),
      fetchList('/pdfs/')
    ])
    courseCount.value  = cCount
    sessionCount.value = sCount
    captureCount.value = capCount
    pdfCount.value     = pCount
    statusCounts.value = { draft: sDraft, capturing: sCapt, processing: sProc, finalized: sFin }
    recentSessions.value = (sessions || []).slice(0, 5)
    recentPdfs.value     = (pdfs    || []).slice(0, 4)
  } catch {
    error.value = 'Failed to load dashboard data. Is the API running?'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <!-- Page header -->
    <div class="page-header flex items-center justify-between">
      <div>
        <h1>Dashboard</h1>
        <p>Overview of your SmartBoard Retrofit system.</p>
      </div>
      <div v-if="loading" class="flex items-center gap-2 text-sm" style="color:var(--muted)">
        <span class="spinner"></span> Loading…
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <!-- Stat cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <router-link to="/courses" class="card stat-card" style="margin-bottom:0; text-decoration:none; cursor:pointer; transition:border-color .15s;">
        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:.5rem;">
          <div>
            <div style="font-size:.75rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:.35rem;">Courses</div>
            <div style="font-size:2rem; font-weight:700; line-height:1; color:var(--text);">{{ courseCount }}</div>
          </div>
          <div style="width:36px; height:36px; border-radius:.5rem; background:color-mix(in srgb,var(--accent) 15%,transparent); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
            <BookOpen style="width:18px; height:18px; color:var(--accent);" />
          </div>
        </div>
      </router-link>

      <router-link to="/sessions" class="card stat-card" style="margin-bottom:0; text-decoration:none; cursor:pointer; transition:border-color .15s;">
        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:.5rem;">
          <div>
            <div style="font-size:.75rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:.35rem;">Sessions</div>
            <div style="font-size:2rem; font-weight:700; line-height:1; color:var(--text);">{{ sessionCount }}</div>
          </div>
          <div style="width:36px; height:36px; border-radius:.5rem; background:color-mix(in srgb,var(--accent) 15%,transparent); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
            <Calendar style="width:18px; height:18px; color:var(--accent);" />
          </div>
        </div>
      </router-link>

      <router-link to="/capture" class="card stat-card" style="margin-bottom:0; text-decoration:none; cursor:pointer; transition:border-color .15s;">
        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:.5rem;">
          <div>
            <div style="font-size:.75rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:.35rem;">Captures</div>
            <div style="font-size:2rem; font-weight:700; line-height:1; color:var(--text);">{{ captureCount }}</div>
          </div>
          <div style="width:36px; height:36px; border-radius:.5rem; background:color-mix(in srgb,var(--accent) 15%,transparent); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
            <Image style="width:18px; height:18px; color:var(--accent);" />
          </div>
        </div>
      </router-link>

      <router-link to="/archive" class="card stat-card" style="margin-bottom:0; text-decoration:none; cursor:pointer; transition:border-color .15s;">
        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:.5rem;">
          <div>
            <div style="font-size:.75rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:.35rem;">PDFs</div>
            <div style="font-size:2rem; font-weight:700; line-height:1; color:var(--text);">{{ pdfCount }}</div>
          </div>
          <div style="width:36px; height:36px; border-radius:.5rem; background:color-mix(in srgb,var(--accent) 15%,transparent); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
            <FileText style="width:18px; height:18px; color:var(--accent);" />
          </div>
        </div>
      </router-link>
    </div>

    <!-- Status breakdown -->
    <div class="card mb-6" style="padding:1rem 1.25rem;">
      <div class="section-title mb-3">Session status breakdown</div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div style="text-align:center;">
          <div style="font-size:1.375rem; font-weight:700; color:var(--muted);">{{ statusCounts.draft }}</div>
          <div class="badge badge-draft" style="margin-top:.25rem;">Draft</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:1.375rem; font-weight:700; color:var(--warning);">{{ statusCounts.capturing }}</div>
          <div class="badge badge-capturing" style="margin-top:.25rem;">Capturing</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:1.375rem; font-weight:700; color:var(--accent);">{{ statusCounts.processing }}</div>
          <div class="badge badge-processing" style="margin-top:.25rem;">Processing</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:1.375rem; font-weight:700; color:var(--success);">{{ statusCounts.finalized }}</div>
          <div class="badge badge-finalized" style="margin-top:.25rem;">Finalized</div>
        </div>
      </div>
    </div>

    <!-- Recent data + quick actions -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">

      <!-- Recent sessions -->
      <div class="card" style="margin-bottom:0;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem;">
          <h2 style="font-size:.9375rem;">Recent Lesson Sessions</h2>
          <router-link to="/sessions" style="font-size:.8125rem; color:var(--accent);">View all →</router-link>
        </div>
        <div v-if="recentSessions.length === 0" class="empty-state" style="padding:1.5rem 1rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <span>No sessions yet</span>
        </div>
        <ul v-else style="margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:.625rem;">
          <li v-for="s in recentSessions" :key="s.id" style="display:flex; align-items:center; justify-content:space-between; gap:.75rem;">
            <div style="min-width:0; flex:1;">
              <div style="font-size:.875rem; color:var(--text); font-weight:500; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ s.title }}</div>
              <div style="font-size:.75rem; color:var(--muted); margin-top:.125rem;">{{ s.course_code ? s.course_code + ' · ' : '' }}{{ s.date }}</div>
            </div>
            <div style="flex-shrink:0;">
              <span :class="'badge badge-' + s.status">{{ s.status }}</span>
            </div>
          </li>
        </ul>
      </div>

      <!-- Quick actions + device status -->
      <div style="display:flex; flex-direction:column; gap:1rem;">
        <div class="card" style="margin-bottom:0;">
          <h2 style="font-size:.9375rem; margin-bottom:.75rem;">Quick Actions</h2>
          <div style="display:flex; flex-wrap:wrap; gap:.5rem;">
            <router-link to="/sessions" class="btn btn-primary btn-sm">+ New Session</router-link>
            <router-link to="/capture" class="btn btn-secondary btn-sm">Open Capture</router-link>
            <router-link to="/archive" class="btn btn-secondary btn-sm">PDF Archive</router-link>
          </div>
        </div>

        <div class="card" style="margin-bottom:0;">
          <h2 style="font-size:.9375rem; margin-bottom:.75rem;">Device Status</h2>
          <div style="display:flex; align-items:center; gap:.625rem;">
            <span style="width:8px; height:8px; border-radius:50%; background:#475569; flex-shrink:0;"></span>
            <span style="font-size:.875rem; color:var(--muted);">ESP32-CAM — not connected</span>
          </div>
          <div style="font-size:.8rem; color:var(--muted); margin-top:.5rem;">Hardware capture unavailable. Use manual image upload.</div>
        </div>

        <div v-if="recentPdfs.length > 0" class="card" style="margin-bottom:0;">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:.75rem;">
            <h2 style="font-size:.9375rem;">Recent PDFs</h2>
            <router-link to="/archive" style="font-size:.8125rem; color:var(--accent);">View all →</router-link>
          </div>
          <ul style="margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:.4rem;">
            <li v-for="p in recentPdfs" :key="p.id" style="display:flex; align-items:center; justify-content:space-between; gap:.5rem;">
              <span style="font-size:.875rem; color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ p.session_title }}</span>
              <a :href="p.file" target="_blank" style="font-size:.8125rem; color:var(--accent); flex-shrink:0;">View →</a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
