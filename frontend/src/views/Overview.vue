<script setup>
import { ref, onMounted } from 'vue'
import { BookOpen, Calendar, Image, FileText } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

const courseCount = ref(0)
const sessionCount = ref(0)
const captureCount = ref(0)
const pdfCount = ref(0)
const statusCounts = ref({ draft: 0, capturing: 0, processing: 0, finalized: 0 })
const recentSessions = ref([])
const recentPdfs = ref([])
const loading = ref(false)
const error = ref('')

async function getCount(url) {
  try {
    const res = await fetch(url)
    if (!res.ok) return 0
    const data = await res.json()
    if (typeof data.count === 'number') return data.count
    if (Array.isArray(data)) return data.length
    if (Array.isArray(data.results)) return data.results.length
    return 0
  } catch (e) {
    return 0
  }
}

async function fetchList(url) {
  try {
    const res = await fetch(url)
    if (!res.ok) return []
    const data = await res.json()
    if (Array.isArray(data)) return data
    if (Array.isArray(data.results)) return data.results
    return []
  } catch (e) {
    return []
  }
}

onMounted(async () => {
  loading.value = true
  error.value = ''
  try {
    const [cCount, sCount, capCount, pCount, sDraft, sCapt, sProc, sFin, sessions, pdfs] = await Promise.all([
      getCount(API_BASE + '/courses/'),
      getCount(API_BASE + '/sessions/'),
      getCount(API_BASE + '/captures/'),
      getCount(API_BASE + '/pdfs/'),
      getCount(API_BASE + '/sessions/?status=draft'),
      getCount(API_BASE + '/sessions/?status=capturing'),
      getCount(API_BASE + '/sessions/?status=processing'),
      getCount(API_BASE + '/sessions/?status=finalized'),
      fetchList(API_BASE + '/sessions/'),
      fetchList(API_BASE + '/pdfs/')
    ])
    courseCount.value = cCount
    sessionCount.value = sCount
    captureCount.value = capCount
    pdfCount.value = pCount
    statusCounts.value = { draft: sDraft, capturing: sCapt, processing: sProc, finalized: sFin }
    recentSessions.value = (sessions || []).slice(0, 5)
    recentPdfs.value = (pdfs || []).slice(0, 3)
  } catch (e) {
    error.value = 'Failed to load dashboard data. Is the API running?'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="p-4">
    <div class="mb-4">
      <h1 class="text-2xl font-semibold text-cyan-400">Dashboard</h1>
      <p class="text-slate-400">Manage lessons and digitized whiteboard notes.</p>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-900/40 border border-red-700 rounded text-red-300">{{ error }}</div>
    <div v-if="loading" class="text-slate-400 mb-4">Loading...</div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
      <router-link to="/courses" class="card p-4 hover:bg-slate-900/50">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-slate-400 text-sm">Courses</div>
            <div class="text-2xl text-cyan-400">{{ courseCount }}</div>
          </div>
          <BookOpen class="w-6 h-6 text-cyan-400" />
        </div>
      </router-link>
      <router-link to="/sessions" class="card p-4 hover:bg-slate-900/50">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-slate-400 text-sm">Lesson sessions</div>
            <div class="text-2xl text-cyan-400">{{ sessionCount }}</div>
          </div>
          <Calendar class="w-6 h-6 text-cyan-400" />
        </div>
      </router-link>
      <router-link to="/capture" class="card p-4 hover:bg-slate-900/50">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-slate-400 text-sm">Captures</div>
            <div class="text-2xl text-cyan-400">{{ captureCount }}</div>
          </div>
          <Image class="w-6 h-6 text-cyan-400" />
        </div>
      </router-link>
      <router-link to="/archive" class="card p-4 hover:bg-slate-900/50">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-slate-400 text-sm">PDFs</div>
            <div class="text-2xl text-cyan-400">{{ pdfCount }}</div>
          </div>
          <FileText class="w-6 h-6 text-cyan-400" />
        </div>
      </router-link>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
      <div class="card p-3 text-center">
        <div class="text-slate-400 text-sm">Draft</div>
        <div class="text-lg text-slate-200">{{ statusCounts.draft }}</div>
      </div>
      <div class="card p-3 text-center">
        <div class="text-slate-400 text-sm">Capturing</div>
        <div class="text-lg text-yellow-300">{{ statusCounts.capturing }}</div>
      </div>
      <div class="card p-3 text-center">
        <div class="text-slate-400 text-sm">Processing</div>
        <div class="text-lg text-blue-300">{{ statusCounts.processing }}</div>
      </div>
      <div class="card p-3 text-center">
        <div class="text-slate-400 text-sm">Finalized</div>
        <div class="text-lg text-green-300">{{ statusCounts.finalized }}</div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
      <div class="card p-4">
        <div class="flex items-center justify-between mb-2">
          <h2 class="text-lg font-semibold text-cyan-400">Recent Lesson Sessions</h2>
          <router-link to="/sessions" class="text-cyan-300 text-sm hover:underline">View all</router-link>
        </div>
        <div v-if="recentSessions.length === 0" class="text-slate-400">No lesson sessions yet</div>
        <ul v-else class="space-y-2">
          <li v-for="s in recentSessions" :key="s.id" class="flex items-center justify-between">
            <router-link :to="'/sessions/' + s.id" class="text-cyan-300 hover:underline">{{ s.title }}</router-link>
            <div class="text-slate-400 text-sm">{{ s.course_code }} - {{ s.date }}</div>
          </li>
        </ul>
      </div>
      <div class="card p-4">
        <div class="flex items-center justify-between mb-2">
          <h2 class="text-lg font-semibold text-cyan-400">Recent PDFs</h2>
          <router-link to="/archive" class="text-cyan-300 text-sm hover:underline">View all</router-link>
        </div>
        <div v-if="recentPdfs.length === 0" class="text-slate-400">No PDFs yet</div>
        <ul v-else class="space-y-2">
          <li v-for="p in recentPdfs" :key="p.id" class="flex items-center justify-between">
            <span class="text-slate-200">{{ p.session_title }}</span>
            <a :href="p.file" target="_blank" class="text-cyan-300 hover:underline text-sm">View</a>
          </li>
        </ul>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
      <div class="card p-4">
        <h2 class="text-lg font-semibold text-cyan-400 mb-2">Device Status</h2>
        <div class="flex items-center gap-2 mb-1">
          <span class="px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-300">ESP32-CAM: Not connected</span>
        </div>
        <div class="text-sm text-slate-400">Hardware capture is not connected yet.</div>
      </div>
      <div class="card p-4">
        <h2 class="text-lg font-semibold text-cyan-400 mb-2">Quick Actions</h2>
        <div class="flex flex-wrap gap-2">
          <router-link to="/sessions" class="px-3 py-2 bg-cyan-400 text-black rounded">New Lesson Session</router-link>
          <router-link to="/capture" class="px-3 py-2 bg-slate-700 text-slate-200 rounded">Open Whiteboard Capture</router-link>
        </div>
      </div>
    </div>
  </div>
</template>