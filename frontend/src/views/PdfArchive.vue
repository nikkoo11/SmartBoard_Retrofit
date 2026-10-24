<script setup>
import { ref, onMounted } from 'vue'
import { Search, FileText, Download, Trash2 } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

const pdfs = ref([])
const sessions = ref([])
const search = ref('')
const loading = ref(false)
const error = ref('')
const selectedSession = ref('')
const generating = ref(false)
const genMsg = ref('')
const genErr = ref('')

async function loadAll(url, acc) {
  let results = acc || []
  let next = url
  while (next) {
    try {
      const res = await fetch(next)
      if (!res.ok) break
      const data = await res.json()
      if (Array.isArray(data)) {
        results = results.concat(data)
        break
      } else if (data.results) {
        results = results.concat(data.results)
        next = data.next
      } else {
        break
      }
    } catch (e) {
      break
    }
  }
  return results
}

async function fetchPdfs() {
  loading.value = true
  error.value = ''
  try {
    const url = search.value ? API_BASE + '/pdfs/?search=' + encodeURIComponent(search.value) : API_BASE + '/pdfs/'
    pdfs.value = await loadAll(url)
  } catch (e) {
    error.value = 'Failed to load PDFs. Is the API running?'
    pdfs.value = []
  } finally {
    loading.value = false
  }
}

async function fetchSessions() {
  sessions.value = await loadAll(API_BASE + '/sessions/')
}

function onSearch() {
  fetchPdfs()
}

async function generatePdf() {
  if (!selectedSession.value) return
  generating.value = true
  genMsg.value = ''
  genErr.value = ''
  try {
    const res = await fetch(API_BASE + '/sessions/' + selectedSession.value + '/generate-pdf/', {
      method: 'POST'
    })
    if (res.status === 400) {
      const data = await res.json()
      genErr.value = data.detail || 'Failed to generate PDF'
    } else if (res.ok || res.status === 201) {
      genMsg.value = 'PDF generated successfully'
      await fetchPdfs()
    } else {
      genErr.value = 'Failed to generate PDF'
    }
  } catch (e) {
    genErr.value = 'Failed to generate PDF'
  } finally {
    generating.value = false
  }
}

async function deletePdf(p) {
  if (!confirm('Delete this PDF?')) return
  try {
    const res = await fetch(API_BASE + '/pdfs/' + p.id + '/', { method: 'DELETE' })
    if (res.ok || res.status === 204) {
      await fetchPdfs()
    } else {
      error.value = 'Failed to delete PDF'
    }
  } catch (e) {
    error.value = 'Failed to delete PDF'
  }
}

function viewPdf(p) {
  if (p.file) {
    window.open(p.file, '_blank')
  }
}

function downloadPdf(p) {
  if (p.file) {
    const a = document.createElement('a')
    a.href = p.file
    a.download = ''
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }
}

onMounted(async () => {
  await fetchSessions()
  await fetchPdfs()
})
</script>

<template>
  <div class="p-4">
    <h1 class="text-2xl font-semibold text-cyan-400 mb-4">PDF Archive</h1>

    <div class="card mb-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-2">Generate PDF</h2>
      <div class="flex flex-wrap items-center gap-2 mb-2">
        <select v-model="selectedSession" class="px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200">
          <option value="">Select a session...</option>
          <option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.course_code }} - {{ s.title }} ({{ s.date }})</option>
        </select>
        <button @click="generatePdf" :disabled="!selectedSession || generating" class="px-3 py-2 bg-cyan-400 text-black rounded disabled:opacity-50">{{ generating ? 'Generating...' : 'Generate PDF' }}</button>
      </div>
      <div v-if="genMsg" class="text-green-400 text-sm">{{ genMsg }}</div>
      <div v-if="genErr" class="text-red-400 text-sm">{{ genErr }}</div>
    </div>

    <div class="mb-4 flex items-center gap-2">
      <div class="relative w-full max-w-sm">
        <Search class="absolute left-2 top-2.5 w-4 h-4 text-slate-400" />
        <input v-model="search" @input="onSearch" placeholder="Search by session or course" class="w-full pl-8 pr-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-200" />
      </div>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-900/40 border border-red-700 rounded text-red-300">{{ error }}</div>

    <div v-if="loading" class="text-slate-400">Loading...</div>

    <div v-else-if="pdfs.length === 0" class="card p-6 text-center">
      <p class="text-slate-400 mb-3">No PDFs yet. Generate one from a session that has captures.</p>
    </div>

    <div v-else class="overflow-x-auto card">
      <table class="w-full">
        <thead>
          <tr class="border-b border-slate-700">
            <th class="text-left p-3 text-slate-300">Course</th>
            <th class="text-left p-3 text-slate-300">Session</th>
            <th class="text-left p-3 text-slate-300">Created</th>
            <th class="text-right p-3 text-slate-300">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in pdfs" :key="p.id" class="border-b border-slate-800 hover:bg-slate-900/50">
            <td class="p-3 text-slate-200">{{ p.course_name }}</td>
            <td class="p-3 text-slate-200">{{ p.session_title }}</td>
            <td class="p-3 text-slate-400">{{ p.created_at }}</td>
            <td class="p-3 text-right flex items-center justify-end gap-2 flex-wrap">
              <button @click="viewPdf(p)" class="px-2 py-1 bg-slate-700 text-slate-200 rounded text-sm flex items-center gap-1"><FileText class="w-4 h-4" /> View</button>
              <button @click="downloadPdf(p)" class="px-2 py-1 bg-slate-700 text-slate-200 rounded text-sm flex items-center gap-1"><Download class="w-4 h-4" /> Download</button>
              <button disabled class="px-2 py-1 bg-slate-800 text-slate-500 rounded text-sm">Gmail not set up yet</button>
              <button @click="deletePdf(p)" class="p-2 hover:bg-red-900/40 text-red-400 rounded"><Trash2 class="w-4 h-4" /></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>