<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
const route = useRoute()
const router = useRouter()
const id = route.params.id

const session = ref(null)
const captures = ref([])
const pdfs = ref([])
const loading = ref(false)
const error = ref('')

async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const [sRes, cRes, pRes] = await Promise.all([
      fetch(API_BASE + '/sessions/' + id + '/'),
      fetch(API_BASE + '/captures/?session=' + id),
      fetch(API_BASE + '/pdfs/?session=' + id)
    ])
    if (sRes.ok) {
      const sd = await sRes.json()
      session.value = sd
    } else {
      error.value = 'Failed to load session'
    }
    if (cRes.ok) {
      const cd = await cRes.json()
      captures.value = Array.isArray(cd) ? cd : (cd.results || [])
    }
    if (pRes.ok) {
      const pd = await pRes.json()
      pdfs.value = Array.isArray(pd) ? pd : (pd.results || [])
    }
  } catch (e) {
    error.value = 'Failed to load session details'
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="p-4">
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-cyan-400">Session Detail</h1>
      <div class="flex items-center gap-3">
        <router-link :to="'/capture?session=' + id" class="px-3 py-2 bg-cyan-400 text-black rounded">Open in Whiteboard Capture</router-link>
        <router-link to="/sessions" class="text-cyan-300 hover:underline">Back to sessions</router-link>
      </div>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-900/40 border border-red-700 rounded text-red-300">{{ error }}</div>
    <div v-if="loading" class="text-slate-400">Loading...</div>

    <div v-if="session" class="card mb-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-slate-400 text-sm">Course</div>
          <div class="text-slate-200">{{ session.course_code }} - {{ session.course_name }}</div>
        </div>
        <div>
          <div class="text-slate-400 text-sm">Title</div>
          <div class="text-slate-200">{{ session.title }}</div>
        </div>
        <div>
          <div class="text-slate-400 text-sm">Date</div>
          <div class="text-slate-200">{{ session.date }}</div>
        </div>
        <div>
          <div class="text-slate-400 text-sm">Status</div>
          <div class="text-slate-200">{{ session.status }}</div>
        </div>
        <div class="col-span-2">
          <div class="text-slate-400 text-sm">Notes</div>
          <div class="text-slate-200 whitespace-pre-wrap">{{ session.notes || '-' }}</div>
        </div>
      </div>
    </div>

    <div class="mb-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-2">Captures</h2>
      <div v-if="captures.length === 0" class="text-slate-400">No captures yet.</div>
      <div v-for="cap in captures" :key="cap.id" class="card mb-3">
        <img :src="cap.image" class="max-w-full mb-2 rounded" />
        <div class="text-slate-300">
          <div class="text-slate-400 text-sm mb-1">Extracted Text</div>
          <div v-if="cap.extracted_text && cap.extracted_text.trim()">{{ cap.extracted_text }}</div>
          <div v-else class="text-slate-500">No text extracted yet (OCR is not connected).</div>
        </div>
      </div>
    </div>

    <div>
      <h2 class="text-lg font-semibold text-cyan-400 mb-2">PDFs</h2>
      <div v-if="pdfs.length === 0" class="text-slate-400">No PDFs yet.</div>
      <ul class="space-y-1">
        <li v-for="p in pdfs" :key="p.id"><a :href="p.file" class="text-cyan-300 hover:underline">{{ p.file }}</a></li>
      </ul>
    </div>
  </div>
</template>