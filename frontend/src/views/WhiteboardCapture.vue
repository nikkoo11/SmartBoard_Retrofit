<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
const route = useRoute()
const router = useRouter()

const sessions = ref([])
const selectedSession = ref('')
const sessionObj = ref(null)
const captures = ref([])
const loadingSessions = ref(false)
const loadingCaptures = ref(false)
const uploading = ref(false)
const error = ref('')
const uploadError = ref('')
const file = ref(null)
const preview = ref('')
const enlarged = ref(null)
const extractedDrafts = ref({})
const finalizing = ref(false)
const finalizeMsg = ref('')

async function loadAllSessions() {
  loadingSessions.value = true
  let all = []
  let url = API_BASE + '/sessions/'
  while (url) {
    try {
      const res = await fetch(url)
      if (!res.ok) break
      const data = await res.json()
      if (Array.isArray(data)) {
        all = all.concat(data)
        break
      } else if (data.results) {
        all = all.concat(data.results)
        url = data.next
      } else {
        break
      }
    } catch (e) {
      break
    }
  }
  sessions.value = all
  loadingSessions.value = false
}

async function fetchSessionObj(id) {
  try {
    const res = await fetch(API_BASE + '/sessions/' + id + '/')
    if (res.ok) {
      sessionObj.value = await res.json()
    }
  } catch (e) {}
}

async function fetchCaptures(id) {
  loadingCaptures.value = true
  try {
    const res = await fetch(API_BASE + '/captures/?session=' + id)
    if (res.ok) {
      const data = await res.json()
      captures.value = Array.isArray(data) ? data : (data.results || [])
      captures.value.forEach(c => {
        extractedDrafts.value[c.id] = c.extracted_text || ''
      })
    } else {
      captures.value = []
    }
  } catch (e) {
    captures.value = []
  } finally {
    loadingCaptures.value = false
  }
}

function onFile(e) {
  const f = e.target.files[0]
  if (!f) return
  file.value = f
  preview.value = URL.createObjectURL(f)
  uploadError.value = ''
}

async function upload() {
  if (!file.value || !selectedSession.value) return
  uploading.value = true
  uploadError.value = ''
  try {
    const fd = new FormData()
    fd.append('session', selectedSession.value)
    fd.append('image', file.value)
    const res = await fetch(API_BASE + '/captures/', {
      method: 'POST',
      body: fd
    })
    if (!res.ok) throw new Error('Upload failed')
    file.value = null
    preview.value = ''
    await fetchCaptures(selectedSession.value)
  } catch (e) {
    uploadError.value = 'Upload failed'
  } finally {
    uploading.value = false
  }
}

function openLarge(c) {
  enlarged.value = c
}

function closeLarge() {
  enlarged.value = null
}

async function saveExtracted(c) {
  try {
    const res = await fetch(API_BASE + '/captures/' + c.id + '/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ extracted_text: extractedDrafts.value[c.id] || '' })
    })
    if (!res.ok) throw new Error('Failed')
    await fetchCaptures(selectedSession.value)
  } catch (e) {
    uploadError.value = 'Failed to save extracted text'
  }
}

async function deleteCapture(c) {
  if (!confirm('Delete this capture?')) return
  try {
    const res = await fetch(API_BASE + '/captures/' + c.id + '/', { method: 'DELETE' })
    if (res.ok || res.status === 204) {
      await fetchCaptures(selectedSession.value)
    } else {
      throw new Error('Failed')
    }
  } catch (e) {
    uploadError.value = 'Failed to delete capture'
  }
}

async function finalizeSession() {
  if (!selectedSession.value) return
  if (!confirm('Finalize this session?')) return
  finalizing.value = true
  finalizeMsg.value = ''
  try {
    const res = await fetch(API_BASE + '/sessions/' + selectedSession.value + '/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'finalized' })
    })
    if (!res.ok) throw new Error('Failed')
    finalizeMsg.value = 'Session marked as finalized. PDF generation is not connected yet, so no PDF was created.'
    await fetchSessionObj(selectedSession.value)
  } catch (e) {
    uploadError.value = 'Failed to finalize session'
  } finally {
    finalizing.value = false
  }
}

watch(selectedSession, async (v) => {
  if (v) {
    await fetchSessionObj(v)
    await fetchCaptures(v)
    finalizeMsg.value = ''
  } else {
    sessionObj.value = null
    captures.value = []
  }
})

onMounted(async () => {
  await loadAllSessions()
  const q = route.query.session
  if (q) {
    selectedSession.value = String(q)
  }
})
</script>

<template>
  <div class="p-4">
    <h1 class="text-2xl font-semibold text-cyan-400 mb-4">Whiteboard Capture</h1>

    <div v-if="sessions.length === 0" class="mb-4 p-3 bg-yellow-900/40 border border-yellow-700 rounded text-yellow-300">
      Create a lesson session first <router-link to="/sessions" class="underline">here</router-link>
    </div>

    <div class="card mb-4">
      <label class="block text-sm text-slate-300 mb-2">Active Session</label>
      <select v-model="selectedSession" class="w-full max-w-md px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200">
        <option value="">Select a session...</option>
        <option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.course_code }} - {{ s.title }} ({{ s.date }})</option>
      </select>
    </div>

    <div class="card mb-4">
      <div class="flex items-center gap-2 mb-1">
        <span class="px-2 py-0.5 rounded text-xs bg-slate-700 text-slate-300">ESP32-CAM: Not connected</span>
      </div>
      <div class="text-sm text-slate-400">Hardware capture is not connected yet. Use manual upload below.</div>
    </div>

    <div v-if="selectedSession" class="mb-4">
      <div class="flex items-center justify-between mb-2">
        <h2 class="text-lg font-semibold text-cyan-400">Manual Upload</h2>
        <button @click="finalizeSession" :disabled="finalizing || (sessionObj && sessionObj.status === 'finalized')" class="px-3 py-2 bg-cyan-400 text-black rounded disabled:opacity-50">Finalize Session</button>
      </div>
      <div class="card">
        <input type="file" accept="image/jpeg,image/png,image/webp" @change="onFile" class="mb-2 text-slate-200" />
        <div v-if="preview" class="mb-2">
          <img :src="preview" class="max-w-xs rounded" />
        </div>
        <button @click="upload" :disabled="!file || uploading" class="px-3 py-2 bg-cyan-400 text-black rounded disabled:opacity-50">{{ uploading ? 'Uploading...' : 'Upload' }}</button>
        <div v-if="uploadError" class="mt-2 text-red-400 text-sm">{{ uploadError }}</div>
        <div v-if="finalizeMsg" class="mt-2 text-green-400 text-sm">{{ finalizeMsg }}</div>
      </div>
    </div>

    <div v-if="selectedSession">
      <h2 class="text-lg font-semibold text-cyan-400 mb-2">Captures</h2>
      <div v-if="loadingCaptures" class="text-slate-400">Loading...</div>
      <div v-else-if="captures.length === 0" class="text-slate-400">No captures for this session yet.</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="c in captures" :key="c.id" class="card">
          <img :src="c.image" class="w-full h-48 object-contain bg-black rounded mb-2 cursor-pointer" @click="openLarge(c)" />
          <div class="mb-2">
            <label class="block text-xs text-slate-400 mb-1">OCR is not connected yet. You can type or edit the text manually.</label>
            <textarea v-model="extractedDrafts[c.id]" class="w-full px-2 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200 h-24"></textarea>
          </div>
          <div class="flex items-center gap-2">
            <button @click="saveExtracted(c)" class="px-2 py-1 bg-cyan-400 text-black rounded text-sm">Save</button>
            <button @click="deleteCapture(c)" class="px-2 py-1 bg-red-900/40 text-red-400 rounded text-sm">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="enlarged" class="fixed inset-0 bg-black/80 flex items-center justify-center z-50" @click="closeLarge">
      <img :src="enlarged.image" class="max-w-full max-h-full" />
    </div>
  </div>
</template>