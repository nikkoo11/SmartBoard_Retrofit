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
const cleaning = ref({})
const cleanMsg = ref({})
const cleanError = ref({})
const extractedDrafts = ref({})
const enlarged = ref(null)
const ocrSource = ref({})
const ocrPsm = ref({})
const ocrCrop = ref({})
const ocrMinConf = ref({})
const ocrFilter = ref({})
const ocrRunning = ref({})
const ocrMsg = ref({})
const ocrErr = ref({})
const ocrConfidence = ref({})
const ocrMs = ref({})
const ocrCropped = ref({})
const ocrWordsDropped = ref({})
const ocrLinesDropped = ref({})
const ocrEngine = ref({})
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
        if (!ocrSource.value[c.id]) ocrSource.value[c.id] = 'threshold'
        if (!ocrPsm.value[c.id]) ocrPsm.value[c.id] = 6
        if (ocrCrop.value[c.id] === undefined) ocrCrop.value[c.id] = true
        if (ocrMinConf.value[c.id] === undefined) ocrMinConf.value[c.id] = 0
        if (ocrFilter.value[c.id] === undefined) ocrFilter.value[c.id] = 'line'
        if (!ocrEngine.value[c.id]) ocrEngine.value[c.id] = 'tesseract'
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

function openLarge(src) {
  enlarged.value = src
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

async function runOcr(c) {
  if ((extractedDrafts.value[c.id] || '').trim()) {
    if (!confirm('Replace existing text with OCR draft?')) return
  }
  ocrRunning.value[c.id] = true
  ocrMsg.value[c.id] = ''
  ocrErr.value[c.id] = ''
  ocrConfidence.value[c.id] = null
  ocrMs.value[c.id] = null
  ocrCropped.value[c.id] = null
  ocrWordsDropped.value[c.id] = null
  ocrLinesDropped.value[c.id] = null
  try {
    const engine = ocrEngine.value[c.id] || 'tesseract'
    let src = ocrSource.value[c.id] || 'threshold'
    if (engine === 'gemini' && src === 'threshold') {
      src = 'original'
      ocrSource.value[c.id] = src
    }
    const psm = ocrPsm.value[c.id] || 6
    const crop = ocrCrop.value[c.id] ? 1 : 0
    const minConf = ocrMinConf.value[c.id] || 0
    const filt = ocrFilter.value[c.id] || 'line'
    const res = await fetch(API_BASE + '/captures/' + c.id + '/ocr/?engine=' + engine + '&source=' + src + '&psm=' + psm + '&crop=' + crop + '&min_conf=' + minConf + '&filter=' + filt + '&save=0', { method: 'POST' })
    if (!res.ok) {
      let detail = 'Cannot reach the backend'
      try { const d = await res.json(); if (d.detail) detail = d.detail } catch (e) {}
      ocrErr.value[c.id] = detail
      return
    }
    const data = await res.json()
    ocrCropped.value[c.id] = data.cropped === true
    ocrWordsDropped.value[c.id] = data.words_dropped || 0
    ocrLinesDropped.value[c.id] = data.lines_dropped || 0
    if (!data.text || !String(data.text).trim()) {
      ocrMsg.value[c.id] = 'No text was detected.'
    } else {
      extractedDrafts.value[c.id] = data.text
      ocrMsg.value[c.id] = 'OCR draft ready. Review it, then press Save.'
      ocrConfidence.value[c.id] = data.confidence
      ocrMs.value[c.id] = data.ms
    }
  } catch (e) {
    ocrErr.value[c.id] = 'Cannot reach the backend'
  } finally {
    ocrRunning.value[c.id] = false
  }
}
async function cleanCapture(c) {
  cleaning.value[c.id] = true
  cleanMsg.value[c.id] = ''
  cleanError.value[c.id] = ''
  try {
    const res = await fetch(API_BASE + '/captures/' + c.id + '/clean/', { method: 'POST' })
    if (!res.ok) {
      let detail = 'Cleaning failed'
      try { const d = await res.json(); if (d.detail) detail = d.detail } catch (e) {}
      cleanError.value[c.id] = detail
      return
    }
    const data = await res.json()
    const idx = captures.value.findIndex(x => x.id === c.id)
    if (idx !== -1) captures.value[idx] = data
    extractedDrafts.value[data.id] = data.extracted_text || ''
    if (data.clean_ms != null) cleanMsg.value[data.id] = 'Cleaned in ' + data.clean_ms + ' ms'
  } catch (e) {
    console.error('Clean image failed:', e)
    cleanError.value[c.id] = 'Cannot reach the backend'
  } finally {
    cleaning.value[c.id] = false
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
  uploadError.value = ''
  try {
    const genRes = await fetch(API_BASE + '/sessions/' + selectedSession.value + '/generate-pdf/', {
      method: 'POST'
    })
    if (genRes.status === 400) {
      try {
        const data = await genRes.json()
        uploadError.value = data.detail || 'Failed to generate PDF'
      } catch (e) {
        uploadError.value = 'Failed to generate PDF'
      }
      return
    }
    if (!(genRes.ok || genRes.status === 201)) {
      uploadError.value = 'Failed to generate PDF'
      return
    }
    const pdfData = await genRes.json()
    const patchRes = await fetch(API_BASE + '/sessions/' + selectedSession.value + '/', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'finalized' })
    })
    if (!patchRes.ok) {
      uploadError.value = 'Failed to finalize session'
      return
    }
    await fetchSessionObj(selectedSession.value)
    let msg = 'Session finalized and PDF created. '
    if (pdfData && pdfData.file) {
      msg += '<a href="' + pdfData.file + '" target="_blank" class="underline">View PDF</a> '
    }
    msg += '<a href="/archive" class="underline">Go to Archive</a>'
    finalizeMsg.value = msg
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
        <div v-if="finalizeMsg" class="mt-2 text-green-400 text-sm" v-html="finalizeMsg"></div>
      </div>
    </div>

    <div v-if="selectedSession">
      <h2 class="text-lg font-semibold text-cyan-400 mb-2">Captures</h2>
      <div v-if="loadingCaptures" class="text-slate-400">Loading...</div>
      <div v-else-if="captures.length === 0" class="text-slate-400">No captures for this session yet.</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div v-for="c in captures" :key="c.id" class="card">
          <div v-if="c.cleaned_image" class="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-2">
            <div>
              <div class="text-xs text-slate-400 mb-1">Original</div>
              <img :src="c.image" class="w-full h-48 object-contain bg-black rounded cursor-pointer" @click="openLarge(c.image)" />
            </div>
            <div>
              <div class="text-xs text-slate-400 mb-1">Cleaned</div>
              <img :src="c.cleaned_image" class="w-full h-48 object-contain bg-black rounded cursor-pointer" @click="openLarge(c.cleaned_image)" />
            </div>
          </div>
          <div v-else class="mb-2">
            <img :src="c.image" class="w-full h-48 object-contain bg-black rounded cursor-pointer" @click="openLarge(c.image)" />
            <div class="text-xs text-slate-500 mt-1">Not cleaned yet.</div>
          </div>
          <div v-if="c.clean_ms != null" class="text-xs text-slate-400 mb-2">Cleaning time: {{ c.clean_ms }} ms</div>
          <div v-if="cleanMsg[c.id]" class="text-xs text-green-400 mb-2">{{ cleanMsg[c.id] }}</div>
          <div v-if="cleanError[c.id]" class="text-xs text-red-400 mb-2">{{ cleanError[c.id] }}</div>
<div class="mb-2">
            <label class="block text-xs text-slate-400 mb-1">OCR results are a draft and may contain mistakes, especially for handwriting. Please review and edit before saving.</label>
            <div class="flex flex-wrap items-center gap-2 mb-2">
              <select v-model="ocrEngine[c.id]" class="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200 text-sm">
                <option value="tesseract">Tesseract</option>
                <option value="gemini">Gemini</option>
              </select>
              <div v-if="ocrEngine[c.id] === 'gemini'" class="text-xs text-cyan-400">Gemini selected</div>
              <select v-model="ocrSource[c.id]" class="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200 text-sm">
                <option value="original">Original</option>
                <option value="cleaned">Cleaned</option>
                <option value="threshold" :disabled="ocrEngine[c.id] === 'gemini'">OCR-optimized (threshold)</option>
              </select>
              <select v-model="ocrPsm[c.id]" :disabled="ocrEngine[c.id] === 'gemini'" class="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200 text-sm disabled:opacity-50">
                <option :value="6">Single block (6)</option>
                <option :value="11">Sparse text (11)</option>
                <option :value="3">Auto (3)</option>
              </select>
              <button @click="runOcr(c)" :disabled="ocrRunning[c.id]" class="px-2 py-1 bg-cyan-400 text-black rounded text-sm disabled:opacity-50">{{ ocrRunning[c.id] ? 'Running OCR...' : 'Run OCR' }}</button>
            </div>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mb-2 text-xs text-slate-300">
              <label class="flex items-center gap-1">
                <input type="checkbox" v-model="ocrCrop[c.id]" :disabled="ocrEngine[c.id] === 'gemini'" class="accent-cyan-400 disabled:opacity-50" />
                Crop to the page/board first
              </label>
              <label class="flex items-center gap-2">
                Noise filter:
                <select v-model.number="ocrMinConf[c.id]" :disabled="ocrEngine[c.id] === 'gemini'" class="px-1 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200 disabled:opacity-50">
                  <option :value="0">Off</option>
                  <option :value="30">Light (30)</option>
                  <option :value="40">Medium (40)</option>
                </select>
              </label>
              <label class="flex items-center gap-2">
                Filter type:
                <select v-model="ocrFilter[c.id]" :disabled="ocrEngine[c.id] === 'gemini'" class="px-1 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200 disabled:opacity-50">
                  <option value="line">Whole lines</option>
                  <option value="word">Single words</option>
                </select>
              </label>
            </div>
            <div v-if="ocrMsg[c.id]" class="text-xs text-green-400 mb-1">{{ ocrMsg[c.id] }}</div>
            <div v-if="ocrEngine[c.id] !== 'gemini' && ocrCropped[c.id] === true" class="text-xs text-slate-400 mb-1">Cropped: yes</div>
            <div v-if="ocrEngine[c.id] !== 'gemini' && ocrCropped[c.id] === false" class="text-xs text-yellow-400 mb-1">Cropped: no — Page not found, used the full photo.</div>
            <div v-if="ocrWordsDropped[c.id] != null && ocrWordsDropped[c.id] > 0" class="text-xs text-slate-400 mb-1">Words removed: {{ ocrWordsDropped[c.id] }}</div>
            <div v-if="ocrLinesDropped[c.id] != null && ocrLinesDropped[c.id] > 0" class="text-xs text-slate-400 mb-1">Lines removed: {{ ocrLinesDropped[c.id] }}</div>
            <div v-if="typeof ocrConfidence[c.id] === 'number'" class="text-xs text-slate-400 mb-1">{{ ocrEngine[c.id] === 'gemini' ? 'Gemini' : 'Tesseract' }} confidence: {{ ocrConfidence[c.id] }}%</div>
            <div v-if="typeof ocrMs[c.id] === 'number'" class="text-xs text-slate-400 mb-1">Time: {{ ocrMs[c.id] }} ms</div>
            <div class="text-xs text-slate-500 mb-1">OCR is a draft. Remove or fix wrong lines before saving.</div>
            <div v-if="ocrErr[c.id]" class="text-xs text-red-400 mb-1">{{ ocrErr[c.id] }}</div>
            <textarea v-model="extractedDrafts[c.id]" class="w-full px-2 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200 h-24"></textarea>
          </div>
          <div class="flex items-center gap-2">
            <button @click="saveExtracted(c)" class="px-2 py-1 bg-cyan-400 text-black rounded text-sm">Save</button>
            <button @click="cleanCapture(c)" :disabled="cleaning[c.id]" class="px-2 py-1 bg-cyan-400 text-black rounded text-sm disabled:opacity-50">{{ cleaning[c.id] ? 'Cleaning...' : (c.cleaned_image ? 'Clean again' : 'Clean image') }}</button>
            <button @click="deleteCapture(c)" class="px-2 py-1 bg-red-900/40 text-red-400 rounded text-sm">Delete</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="enlarged" class="fixed inset-0 bg-black/80 flex items-center justify-center z-50" @click="closeLarge">
      <img :src="enlarged" class="max-w-full max-h-full" />
    </div>
  </div>
</template>
