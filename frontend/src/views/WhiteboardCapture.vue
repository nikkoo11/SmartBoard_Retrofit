<script setup>
import { ref, onMounted, watch, onBeforeUnmount, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, request } from '../services/api.js'

const route    = useRoute()
const router   = useRouter()

const sessions        = ref([])
const selectedSession = ref('')
const sessionObj      = ref(null)
const captures        = ref([])
const processingCount  = computed(() => captures.value.filter(c => c.status === 'processing').length)
const waitingCount     = computed(() => captures.value.filter(c => c.status === 'queued').length)
const failedCount      = computed(() => captures.value.filter(c => c.status === 'failed').length)
const loadingSessions = ref(false)
const loadingCaptures = ref(false)
const isMounted        = ref(true)
const simulatorEnabled = import.meta.env.VITE_ENABLE_DEVICE_SIMULATOR === 'true'
const simulatorStatus  = ref('')
const simulatorStatusType = ref('info')
const holdProgress     = ref(0)
const holdCompleted    = ref(false)
let holdTimer          = null
let holdInterval       = null
const knownCaptureIds   = ref(new Set())
const loadedSessionId   = ref(null)
const pollingInProgress = ref(false)
const error           = ref('')
const uploadStep       = ref('')

// ---- FIX 1: these five were used in the code but never created ----
const uploading       = ref(false)
const uploadError     = ref('')
const finalizing      = ref(false)
const isHolding       = ref(false)
let capturePoll       = null
// -------------------------------------------------------------------

const file            = ref(null)
const preview         = ref('')
const cameraOpen      = ref(false)
const cameraError     = ref('')
const videoEl         = ref(null)
let cameraStream      = null
const cleaning        = ref({})
const cleanMsg        = ref({})
const cleanError      = ref({})
const extractedDrafts = ref({})
const enlarged        = ref(null)
const ocrSource       = ref({})
const ocrPsm          = ref({})
const ocrCrop         = ref({})
const ocrMinConf      = ref({})
const ocrFilter       = ref({})
const ocrRunning      = ref({})
const ocrMsg          = ref({})
const ocrErr          = ref({})
const ocrConfidence   = ref({})
const ocrMs           = ref({})
const ocrCropped      = ref({})
const ocrWordsDropped = ref({})
const ocrLinesDropped = ref({})
const ocrEngine       = ref({})
const processingCaptureIds = ref(new Set())
const processedCaptureIds = ref(new Set(JSON.parse(localStorage.getItem('smartboard_processed_captures') || '[]')))
const finalizeMsg     = ref('')
const copiedId        = ref(null)

async function loadAllSessions() {
  loadingSessions.value = true
  let all = [], url = '/sessions/'
  while (url) {
    try {
      const data = await request(url)
      if (Array.isArray(data)) { all = all.concat(data); break }
      else if (data.results) { all = all.concat(data.results); url = data.next }
      else break
    } catch { break }
  }
  sessions.value = all; loadingSessions.value = false
}

async function fetchSessionObj(id) {
  try { const s = await api.session(id); sessionObj.value = s } catch {}
}

function markProcessed(id) {
  const next = new Set(processedCaptureIds.value)
  next.add(id)
  processedCaptureIds.value = next
  try { localStorage.setItem('smartboard_processed_captures', JSON.stringify([...next])) } catch {}
}

async function processCapture(c) {
  if (!c || !c.id) return
  if (processedCaptureIds.value.has(c.id) || processingCaptureIds.value.has(c.id)) return
  const next = new Set(processingCaptureIds.value)
  next.add(c.id)
  processingCaptureIds.value = next
  try {
    if (isMounted.value) ocrSource.value[c.id] = 'cleaned'
    try { await cleanCapture(c) } catch {}
    const updated = captures.value.find(x => x.id === c.id) || c
    const online = typeof navigator !== 'undefined' ? navigator.onLine : true
    if (online) {
      if (isMounted.value) ocrEngine.value[updated.id] = 'gemini'
      await runOcr(updated)
      if (isMounted.value && ocrErr.value[updated.id]) {
        if (isMounted.value) ocrEngine.value[updated.id] = 'tesseract'
        if (isMounted.value) ocrErr.value[updated.id] = ''
        await runOcr(updated)
      }
    } else {
      if (isMounted.value) ocrEngine.value[updated.id] = 'tesseract'
      await runOcr(updated)
    }
    const text = extractedDrafts.value[updated.id]
    if (text && String(text).trim()) {
      await api.updateCapture(updated.id, { extracted_text: text })
      try { await api.generateCapturePdf(updated.id) } catch {}
    }
    markProcessed(c.id)
  } catch {}
  finally {
    const done = new Set(processingCaptureIds.value)
    done.delete(c.id)
    processingCaptureIds.value = done
  }
}

// FIX 2: loadingCaptures is now reset in finally (it used to stay true forever,
// which hid the captures list). "silent" is used by the 5-second poll so the
// list does not flicker. Network errors no longer clear the list.
async function fetchCaptures(id, silent = false) {
  if (isMounted.value && !silent) loadingCaptures.value = true
  try {
    const data = await api.captures('?session=' + id)
    if (!isMounted.value) return
    if (String(selectedSession.value) !== String(id)) return
    captures.value = Array.isArray(data) ? data : (data.results || [])
    captures.value.forEach(c => {
      // keep what the user is editing; only fill the draft the first time
      if (extractedDrafts.value[c.id] === undefined) extractedDrafts.value[c.id] = c.extracted_text || ''
      if (!ocrSource.value[c.id]) ocrSource.value[c.id] = 'threshold'
      if (!ocrPsm.value[c.id]) ocrPsm.value[c.id] = 6
      if (ocrCrop.value[c.id] === undefined) ocrCrop.value[c.id] = true
      if (ocrMinConf.value[c.id] === undefined) ocrMinConf.value[c.id] = 0
      if (ocrFilter.value[c.id] === undefined) ocrFilter.value[c.id] = 'line'
      if (!ocrEngine.value[c.id]) ocrEngine.value[c.id] = 'tesseract'
    })
    const sid = String(id)
    const isFirstLoad = loadedSessionId.value !== sid
    if (isFirstLoad) {
      knownCaptureIds.value = new Set()
      loadedSessionId.value = sid
    }
    for (const c of captures.value) {
      if (!knownCaptureIds.value.has(c.id)) {
        knownCaptureIds.value = new Set([...knownCaptureIds.value, c.id])
        if (!isFirstLoad && !processedCaptureIds.value.has(c.id) && !processingCaptureIds.value.has(c.id)) {
          processCapture(c)
        }
      }
    }
  } catch {
    // keep the old list when the network fails
  } finally {
    if (isMounted.value && !silent) loadingCaptures.value = false
  }
}

async function openCamera() {
  cameraError.value = ''
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    cameraError.value = 'Camera is not supported in this browser.'
    return
  }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    cameraOpen.value = true
    await (new Promise(resolve => setTimeout(resolve, 0)))
    if (videoEl.value) videoEl.value.srcObject = cameraStream
  } catch (e) {
    cameraError.value = e && e.message ? e.message : 'Camera permission denied or unavailable.'
    stopCamera()
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(t => t.stop())
    cameraStream = null
  }
  cameraOpen.value = false
  if (videoEl.value) videoEl.value.srcObject = null
}

function cancelCamera() { stopCamera() }

async function captureFrame() {
  if (!videoEl.value) return
  const video = videoEl.value
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth || 640
  canvas.height = video.videoHeight || 480
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  canvas.toBlob(async (blob) => {
    if (!blob) { cameraError.value = 'Failed to capture frame.'; return }
    const f = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' })
    file.value = f
    preview.value = URL.createObjectURL(f)
    stopCamera()
    await upload()
  }, 'image/jpeg', 0.92)
}

function retake() {
  file.value = null
  preview.value = ''
  openCamera()
}

const selectedFiles    = ref([])
const fileStatuses     = ref({})

function triggerSimulatorFilePicker() {
  if (holdCompleted.value) { holdCompleted.value = false; return }
  const input = document.getElementById('simulator-file-upload')
  if (input) input.click()
}

function startHold() {
  if (!selectedSession.value || uploading.value || finalizing.value) return
  holdCompleted.value = false
  isHolding.value = true
  holdProgress.value = 0
  const start = Date.now()
  holdInterval = setInterval(() => {
    holdProgress.value = Math.min(100, ((Date.now() - start) / 1500) * 100)
  }, 50)
  holdTimer = setTimeout(async () => {
    clearInterval(holdInterval)
    holdInterval = null
    isHolding.value = false
    holdProgress.value = 0
    holdCompleted.value = true
    await finalizeFromSimulator()
  }, 1500)
}

function cancelHold() {
  if (holdTimer) { clearTimeout(holdTimer); holdTimer = null }
  if (holdInterval) { clearInterval(holdInterval); holdInterval = null }
  isHolding.value = false
  holdProgress.value = 0
}

async function waitForPendingCaptures() {
  const start = Date.now()
  while (processingCaptureIds.value.size > 0) {
    if (Date.now() - start > 30000) {
      simulatorStatus.value = 'Timed out waiting for pending captures.'
      simulatorStatusType.value = 'error'
      return
    }
    await new Promise(resolve => setTimeout(resolve, 250))
  }
}

async function finalizeFromSimulator() {
  if (!selectedSession.value || finalizing.value) return
  finalizing.value = true
  await waitForPendingCaptures()
  const successful = captures.value.filter(c => c.extracted_text && String(c.extracted_text).trim())
  if (successful.length === 0) {
    simulatorStatus.value = 'No captures with saved text. PDF not generated.'
    simulatorStatusType.value = 'error'
    finalizing.value = false
    return
  }
  const failed = captures.value.filter(c => !c.extracted_text || !String(c.extracted_text).trim())
  if (failed.length) {
    const failedIds = failed.map(c => c.id).join(', ')
    simulatorStatus.value = `Finalizing with ${successful.length} capture(s); ${failed.length} failed or skipped: ${failedIds}.`
    simulatorStatusType.value = 'error'
  } else {
    simulatorStatus.value = `Finalizing ${successful.length} capture(s)...`
    simulatorStatusType.value = 'info'
  }
  try {
    await api.generatePdf(selectedSession.value)
    try {
      await api.updateSession(selectedSession.value, { status: 'finalized' })
      await fetchSessionObj(selectedSession.value)
      if (failed.length) {
        const failedIds = failed.map(c => c.id).join(', ')
        simulatorStatus.value = `PDF generated from ${successful.length} capture(s). ${failed.length} failed or skipped: ${failedIds}.`
        simulatorStatusType.value = 'warn'
      } else {
        simulatorStatus.value = 'Session finalized and PDF generated.'
        simulatorStatusType.value = 'success'
      }
    } catch {
      simulatorStatus.value = 'PDF was created but the session status was not updated.'
      simulatorStatusType.value = 'warn'
    }
  } catch (e) {
    simulatorStatus.value = e && e.message ? e.message : 'Finalization failed.'
    simulatorStatusType.value = 'error'
  } finally {
    finalizing.value = false
  }
}

function onSimulatorFile(e) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  if (!f.type.startsWith('image/')) { simulatorStatus.value = 'Please select an image file.'; simulatorStatusType.value = 'error'; e.target.value = ''; return }
  if (f.size > 10 * 1024 * 1024) { simulatorStatus.value = 'Image is too large (max 10 MB).'; simulatorStatusType.value = 'error'; e.target.value = ''; return }
  file.value = f
  preview.value = URL.createObjectURL(f)
  simulatorStatus.value = 'Processing capture...'
  simulatorStatusType.value = 'info'
  upload()
  e.target.value = ''
}

function onFile(e) {
  const fs = Array.from(e.target.files || [])
  selectedFiles.value = selectedFiles.value.concat(fs)
  if (fs.length) { file.value = fs[0]; preview.value = URL.createObjectURL(fs[0]) }
  e.target.value = ''
}

async function processAllSelected() {
  if (!selectedFiles.value.length || !selectedSession.value) return
  for (const f of [...selectedFiles.value]) {
    file.value = f
    preview.value = URL.createObjectURL(f)
    fileStatuses.value[f.name] = 'processing'
    uploadError.value = ''
    try {
      await upload()
      // upload() does not throw, it sets uploadError, so check it here
      fileStatuses.value[f.name] = uploadError.value ? 'failed' : 'done'
    } catch (e) {
      fileStatuses.value[f.name] = 'failed'
    }
  }
  file.value = null
  preview.value = ''
  selectedFiles.value = []
}

async function upload() {
  if (!file.value) { uploadError.value = 'Please choose an image first.'; return }
  if (!selectedSession.value) { uploadError.value = 'Please select or start a session first.'; return }
  const sessionExists = sessions.value.some(s => String(s.id) === String(selectedSession.value))
  if (!sessionExists) {
    selectedSession.value = ''
    router.replace({ path: route.path, query: { ...route.query, session: undefined } })
    uploadError.value = 'Please select or start a session first.'
    return
  }
  if (uploading.value) return
  uploading.value = true; uploadError.value = ''; uploadStep.value = 'Uploading...'
  try {
    const fd = new FormData(); fd.append('session', selectedSession.value); fd.append('image', file.value)
    const created = await api.createCapture(fd)
    markProcessed(created.id)
    file.value = null; preview.value = ''
    await fetchCaptures(selectedSession.value, true)
    const capture = captures.value.find(c => c.id === created.id)
    if (capture) {
      ocrSource.value[capture.id] = 'cleaned'
      uploadStep.value = 'Cleaning photo...'
      try {
        await cleanCapture(capture)
      } catch (e) {
        cleanError.value[capture.id] = e && e.message ? e.message : 'Cleaning failed'
      }
      const updated = captures.value.find(c => c.id === created.id) || capture
      const online = typeof navigator !== 'undefined' ? navigator.onLine : true
      try {
        if (online) {
          ocrEngine.value[updated.id] = 'gemini'
          uploadStep.value = 'Reading text with Gemini...'
          await runOcr(updated)
          if (ocrErr.value[updated.id]) {
            ocrEngine.value[updated.id] = 'tesseract'
            ocrErr.value[updated.id] = ''
            uploadStep.value = 'Gemini failed, using offline reader...'
            await runOcr(updated)
          }
        } else {
          ocrEngine.value[updated.id] = 'tesseract'
          uploadStep.value = 'Reading text with Tesseract...'
          await runOcr(updated)
        }
      } catch (e) {
        ocrErr.value[updated.id] = e && e.message ? e.message : 'OCR failed'
      }
      const text = extractedDrafts.value[updated.id]
      if (text && String(text).trim()) {
        uploadStep.value = 'Saving text...'
        try {
          await api.updateCapture(updated.id, { extracted_text: text })
        } catch (e) {
          uploadError.value = e && e.message ? e.message : 'Failed to save extracted text'
          uploadStep.value = ''
          return
        }
        try {
          await api.generatePdf(selectedSession.value)
          uploadStep.value = 'Done'
          setTimeout(() => { uploadStep.value = '' }, 1500)
          finalizeMsg.value = 'Capture processed, text saved, and PDF generated.'
        } catch (e) {
          uploadError.value = e && e.message ? e.message : 'Text saved, but PDF generation failed'
          uploadStep.value = ''
        }
        await fetchCaptures(selectedSession.value, true)
      } else {
        // show the real OCR reason if there is one
        uploadError.value = ocrErr.value[updated.id]
          ? 'OCR failed: ' + ocrErr.value[updated.id]
          : 'OCR did not return usable text.'
        uploadStep.value = ''
      }
    }
  } catch (e) {
    const detail = e && e.message ? e.message : ''
    uploadError.value = detail || 'Upload failed. Check file type and session.'
    uploadStep.value = ''
  } finally { uploading.value = false; if (uploadStep.value !== 'Done') uploadStep.value = '' }
}

async function saveExtracted(c) {
  try {
    await api.updateCapture(c.id, { extracted_text: extractedDrafts.value[c.id] || '' })
    ocrMsg.value[c.id] = 'Text saved successfully.'
    await fetchCaptures(selectedSession.value, true)
  } catch { uploadError.value = 'Failed to save extracted text' }
}

async function copyText(id) {
  try {
    await navigator.clipboard.writeText(extractedDrafts.value[id] || '')
    copiedId.value = id; setTimeout(() => { copiedId.value = null }, 2000)
  } catch {}
}

async function runOcr(c) {
  if ((extractedDrafts.value[c.id] || '').trim()) {
    if (!confirm('Replace existing text with new OCR result?')) return
  }
  ocrRunning.value[c.id] = true
  ocrMsg.value[c.id] = ''; ocrErr.value[c.id] = ''; ocrConfidence.value[c.id] = null
  ocrMs.value[c.id] = null; ocrCropped.value[c.id] = null
  ocrWordsDropped.value[c.id] = null; ocrLinesDropped.value[c.id] = null
  try {
    const engine  = ocrEngine.value[c.id] || 'tesseract'
    let src       = ocrSource.value[c.id] || 'threshold'
    if (engine === 'gemini' && src === 'threshold') { src = 'original'; ocrSource.value[c.id] = src }
    const psm     = ocrPsm.value[c.id] || 6
    const crop    = ocrCrop.value[c.id] ? 1 : 0
    const minConf = ocrMinConf.value[c.id] || 0
    const filt    = ocrFilter.value[c.id] || 'line'
    const data = await api.ocrCapture(c.id, `engine=${engine}&source=${src}&psm=${psm}&crop=${crop}&min_conf=${minConf}&filter=${filt}&save=0`)
    ocrCropped.value[c.id]      = data.cropped === true
    ocrWordsDropped.value[c.id] = data.words_dropped || 0
    ocrLinesDropped.value[c.id] = data.lines_dropped || 0
    if (!data.text || !String(data.text).trim()) {
      ocrMsg.value[c.id] = 'No text was detected.'
    } else {
      extractedDrafts.value[c.id] = data.text
      ocrMsg.value[c.id]           = 'OCR draft ready — review before saving.'
      ocrConfidence.value[c.id]    = data.confidence
      ocrMs.value[c.id]            = data.ms
    }
  } catch (e) { ocrErr.value[c.id] = e.message || 'Cannot reach the backend' }
  finally { ocrRunning.value[c.id] = false }
}

async function cleanCapture(c) {
  if (cleaning.value[c.id]) return
  cleaning.value[c.id] = true; cleanMsg.value[c.id] = ''; cleanError.value[c.id] = ''
  try {
    const data = await api.cleanCapture(c.id)
    const idx = captures.value.findIndex(x => x.id === c.id)
    if (idx !== -1) captures.value[idx] = data
    extractedDrafts.value[data.id] = data.extracted_text || ''
    if (data.clean_ms != null) cleanMsg.value[data.id] = `Cleaned in ${data.clean_ms} ms`
  } catch (e) { cleanError.value[c.id] = e.message || 'Cleaning failed' }
  finally { cleaning.value[c.id] = false }
}

async function deleteCapture(c) {
  if (!confirm('Delete this capture?')) return
  try {
    await api.deleteCapture(c.id)
    await fetchCaptures(selectedSession.value, true)
  } catch { uploadError.value = 'Failed to delete capture' }
}

async function finalizeSession() {
  if (!selectedSession.value) return
  if (!confirm('Finalize this session and generate a PDF?')) return
  finalizing.value = true; finalizeMsg.value = ''; uploadError.value = ''
  try {
    let pdfData
    try {
      pdfData = await api.generatePdf(selectedSession.value)
    } catch (e) {
      uploadError.value = e.status === 400 ? (e.message || 'Failed to generate PDF') : 'Failed to generate PDF'
      return
    }
    try {
      await api.updateSession(selectedSession.value, { status: 'finalized' })
    } catch {
      uploadError.value = 'Failed to finalize session'
      return
    }
    await fetchSessionObj(selectedSession.value)
    let msg = 'Session finalized and PDF created.'
    if (pdfData?.file) msg += ' <a href="' + pdfData.file + '" target="_blank" style="text-decoration:underline;color:var(--success);">View PDF</a>'
    finalizeMsg.value = msg
  } finally { finalizing.value = false }
}

// FIX 3: the 5-second timer used to only set a flag and never refresh anything.
// Now it really reloads the captures so the status badges update.
watch(selectedSession, async (v) => {
  cancelHold()
  simulatorStatus.value = ''
  const current = route.query.session
  if (String(current || '') !== String(v || '')) {
    router.replace({ path: route.path, query: { ...route.query, session: v || undefined } })
  }
  if (capturePoll) { clearInterval(capturePoll); capturePoll = null }
  captures.value = []
  if (v) {
    await fetchSessionObj(v)
    await fetchCaptures(v)
    if (isMounted.value) finalizeMsg.value = ''
    if (!isMounted.value) return
    capturePoll = setInterval(async () => {
      if (pollingInProgress.value || uploading.value) return
      pollingInProgress.value = true
      try { await fetchCaptures(v, true) }
      finally { pollingInProgress.value = false }
    }, 5000)
  }
  else { if (isMounted.value) { sessionObj.value = null; captures.value = [] } }
})

onBeforeUnmount(() => {
  isMounted.value = false
  try { cancelHold() } catch (err) { console.error('[SmartBoard] unmount cleanup', err) }
  try { stopCamera() } catch (err) { console.error('[SmartBoard] unmount cleanup', err) }
  try { if (capturePoll) clearInterval(capturePoll) } catch (err) { console.error('[SmartBoard] unmount cleanup', err) }
})
onMounted(async () => {
  await loadAllSessions()
  const q = route.query.session
  if (q) {
    const exists = sessions.value.some(s => String(s.id) === String(q))
    if (exists) selectedSession.value = String(q)
    else router.replace({ path: route.path, query: { ...route.query, session: undefined } })
  }
})
</script>

<template>
  <div>
    <div class="page-header">
      <h1>Whiteboard Capture</h1>
      <p>Upload board images, clean them, run OCR, and finalize your session.</p>
    </div>

    <!-- No sessions yet -->
    <div v-if="sessions.length === 0 && !loadingSessions" class="alert alert-warn">
      No lesson sessions found. <router-link to="/sessions">Create a session</router-link> first.
    </div>

    <!-- Session selector -->
    <div class="card mb-4">
      <label style="display:block; font-size:.8125rem; font-weight:500; color:var(--muted); margin-bottom:.5rem;">Active Session</label>
      <div style="display:flex; align-items:center; gap:.75rem; flex-wrap:wrap;">
        <select v-model="selectedSession" style="flex:1; min-width:200px; max-width:480px;">
          <option value="">Select a session…</option>
          <option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.course_code }} – {{ s.title }} ({{ s.date }})</option>
        </select>
        <div v-if="sessionObj" style="display:flex; align-items:center; gap:.5rem;">
          <span :class="'badge badge-' + sessionObj.status">{{ sessionObj.status }}</span>
        </div>
      </div>
      <div style="display:flex; align-items:center; gap:.625rem; margin-top:.75rem;">
        <span style="width:8px; height:8px; border-radius:50%; background:#475569; flex-shrink:0;"></span>
        <span style="font-size:.8125rem; color:var(--muted);">ESP32-CAM hardware not connected — use manual upload below.</span>
      </div>
    </div>

    <!-- Upload + Finalize -->
    <div v-if="selectedSession" class="card mb-4">
      <div style="display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; margin-bottom:.75rem;">
        <button class="btn btn-secondary btn-sm" @click="openCamera" :disabled="cameraOpen || uploading">Scan with Camera</button>
        <button v-if="cameraOpen" class="btn btn-primary btn-sm" @click="captureFrame">Capture Whiteboard</button>
        <button v-if="cameraOpen" class="btn btn-secondary btn-sm" @click="cancelCamera">Cancel Camera</button>
        <button v-if="file && preview && !cameraOpen" class="btn btn-secondary btn-sm" @click="retake">Retake</button>
      </div>
      <div v-if="cameraError" class="alert alert-error" style="margin-bottom:.75rem;">{{ cameraError }}</div>
      <div v-if="cameraOpen" style="margin-bottom:.75rem; text-align:center;">
        <video ref="videoEl" autoplay playsinline muted style="max-width:100%; border-radius:.5rem; border:1px solid var(--border);"></video>
      </div>
      <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:.75rem; margin-bottom:1rem;">
        <h2 style="font-size:.9375rem; margin:0;">Upload Image</h2>
        <button
          class="btn btn-primary btn-sm"
          @click="finalizeSession"
          :disabled="finalizing || (sessionObj && sessionObj.status === 'finalized')"
        >
          <span v-if="finalizing" class="spinner" style="width:13px;height:13px;border-width:2px;"></span>
          {{ finalizing ? 'Finalizing…' : sessionObj && sessionObj.status === 'finalized' ? '✓ Session Finalized' : 'Finalize Session' }}
        </button>
      </div>

      <!-- Drop zone style upload -->
      <div style="border:2px dashed var(--border); border-radius:.5rem; padding:1.25rem; text-align:center; margin-bottom:.875rem; transition:border-color .15s;">
        <input type="file" id="file-upload" accept="image/jpeg,image/png,image/webp" multiple @change="onFile" style="display:none;" />
        <label for="file-upload" style="cursor:pointer; display:flex; flex-direction:column; align-items:center; gap:.5rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="width:32px;height:32px;color:var(--muted);"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <span style="font-size:.875rem; color:var(--muted);">{{ file ? file.name : 'Click to select an image (JPG, PNG, WEBP)' }}</span>
        </label>
      </div>

      <div v-if="preview" style="margin-bottom:.875rem; text-align:center;">
        <img :src="preview" style="max-height:220px; max-width:100%; border-radius:.5rem; border:1px solid var(--border);" />
      </div>

      <div style="display:flex; align-items:center; gap:.5rem; flex-wrap:wrap;">
        <button class="btn btn-primary" @click="upload" :disabled="!file || uploading || !selectedSession">
          <span v-if="uploading" class="spinner" style="width:14px;height:14px;border-width:2px;"></span>
          {{ uploading ? 'Uploading…' : 'Upload' }}
        </button>
        <span v-if="!selectedSession" style="font-size:.8125rem; color:var(--muted);">Start a session first</span>
        <span v-else-if="!file" style="font-size:.8125rem; color:var(--muted);">Choose an image first</span>
        <button v-if="file" class="btn btn-secondary btn-sm" @click="file=null; preview=''">Clear</button>
      </div>

      <div v-if="uploadStep" class="alert alert-info" style="margin-top:.75rem; margin-bottom:0;">
        <span class="spinner" style="width:12px;height:12px;border-width:2px; margin-right:.5rem;"></span>{{ uploadStep }}
      </div>
      <div v-if="uploadError" class="alert alert-error" style="margin-top:.75rem; margin-bottom:0;">{{ uploadError }}</div>
      <div v-if="finalizeMsg" class="alert alert-success" style="margin-top:.75rem; margin-bottom:0;" v-html="finalizeMsg"></div>
    </div>

    <!-- Selected files -->
    <div v-if="selectedFiles.length" class="card mb-4">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:.5rem;">
        <h2 style="font-size:.9375rem; margin:0;">Selected images</h2>
        <button class="btn btn-primary btn-sm" @click="processAllSelected" :disabled="uploading">Process all</button>
      </div>
      <ul style="list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:.375rem;">
        <li v-for="f in selectedFiles" :key="f.name" style="display:flex; align-items:center; justify-content:space-between; gap:.5rem;">
          <span style="font-size:.8125rem; color:var(--text);">{{ f.name }}</span>
          <span style="font-size:.75rem; color:var(--muted);">{{ fileStatuses[f.name] || 'pending' }}</span>
          <button class="btn btn-ghost btn-sm" @click="selectedFiles = selectedFiles.filter(x => x !== f)" :disabled="uploading">Remove</button>
        </li>
      </ul>
    </div>

    <!-- Device Simulator -->
    <div v-if="simulatorEnabled" class="card mb-4">
      <div class="section-title">Device Button Simulator</div>
      <p style="font-size:.8125rem; color:var(--muted); margin-bottom:.75rem;">Tap = capture one image. Hold ~1.5s = end session and generate PDF.</p>
      <input type="file" id="simulator-file-upload" accept="image/*" style="display:none;" @change="onSimulatorFile" />
      <div style="display:flex; align-items:center; gap:.75rem; flex-wrap:wrap;">
        <button
          class="btn btn-primary"
          :disabled="uploading || finalizing || !selectedSession"
          @pointerdown.prevent="startHold"
          @pointerup.prevent="cancelHold"
          @pointerleave="cancelHold"
          @pointercancel="cancelHold"
          @contextmenu.prevent
          @click.prevent="triggerSimulatorFilePicker"
        >
          {{ isHolding ? 'Hold to finalize...' : 'Simulator button' }}
        </button>
        <button class="btn btn-secondary btn-sm" @click="finalizeFromSimulator" :disabled="finalizing || uploading || !selectedSession">
          End session and make PDF
        </button>
      </div>
      <div v-if="isHolding" style="margin-top:.75rem;">
        <div style="height:6px; background:var(--border); border-radius:3px; overflow:hidden;">
          <div :style="'width:' + holdProgress + '%; height:100%; background:var(--accent); transition:width .05s linear;'" ></div>
        </div>
      </div>
      <div v-if="simulatorStatus" :class="simulatorStatusType === 'error' ? 'alert alert-error' : simulatorStatusType === 'success' ? 'alert alert-success' : simulatorStatusType === 'warn' ? 'alert alert-warn' : 'alert alert-info'" style="margin-top:.75rem; margin-bottom:0;">{{ simulatorStatus }}</div>
      <div v-if="!selectedSession" class="alert alert-warn" style="margin-top:.75rem; margin-bottom:0;">Start a session first.</div>
    </div>

    <div v-if="selectedSession && (processingCount || waitingCount || failedCount)" style="font-size:.8125rem; color:var(--muted); margin-bottom:.75rem;">
      {{ processingCount }} processing, {{ waitingCount }} waiting, {{ failedCount }} failed
    </div>

    <!-- Captures grid -->
    <div v-if="selectedSession">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:.875rem;">
        <h2 style="font-size:.9375rem; margin:0;">
          Captures
          <span style="font-size:.8rem; font-weight:400; color:var(--muted); margin-left:.5rem;">{{ captures.length }}</span>
        </h2>
      </div>

      <div v-if="loadingCaptures" class="flex items-center gap-2" style="color:var(--muted); font-size:.875rem; margin-bottom:1rem;">
        <span class="spinner"></span> Loading captures…
      </div>
      <div v-else-if="captures.length === 0" class="card">
        <div class="empty-state" style="padding:1.5rem 1rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          <span>No captures yet. Upload an image above to get started.</span>
        </div>
      </div>

      <div v-else style="display:flex; flex-direction:column; gap:1.25rem;">
        <div v-for="c in captures" :key="c.id" class="card" style="margin-bottom:0;">

          <!-- Status badge -->
          <div v-if="c.status" style="margin-bottom:.625rem;">
            <span v-if="c.status === 'queued'" class="badge" style="background:var(--surface-2); color:var(--muted);">Waiting</span>
            <span v-else-if="c.status === 'processing'" class="badge badge-processing" style="display:inline-flex; align-items:center; gap:.375rem;">
              <span class="spinner" style="width:10px; height:10px; border-width:2px;"></span> Processing…
            </span>
            <span v-else-if="c.status === 'done'" class="badge badge-finalized">Done</span>
            <span v-else-if="c.status === 'failed'" class="badge badge-capturing">Failed</span>
            <div v-if="c.status === 'failed' && c.error_message" style="font-size:.75rem; color:var(--danger); margin-top:.375rem;">{{ c.error_message }}</div>
          </div>

          <!-- Images row -->
          <div :style="c.cleaned_image ? 'display:grid; grid-template-columns:1fr 1fr; gap:.75rem; margin-bottom:1rem;' : 'margin-bottom:1rem;'">
            <div>
              <div style="font-size:.7rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:.375rem;">Original</div>
              <img :src="c.image" loading="lazy" decoding="async" @click="enlarged = c.image" />
            </div>
            <div v-if="c.cleaned_image">
              <div style="font-size:.7rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:.375rem;">Cleaned</div>
              <img :src="c.cleaned_image" loading="lazy" decoding="async" @click="enlarged = c.cleaned_image" />
            </div>
          </div>

          <!-- Clean action feedback -->
          <div v-if="cleanMsg[c.id]" class="alert alert-success" style="margin-bottom:.75rem;">{{ cleanMsg[c.id] }}</div>
          <div v-if="cleanError[c.id]" class="alert alert-error" style="margin-bottom:.75rem;">{{ cleanError[c.id] }}</div>

          <!-- ── OCR Panel ── -->
          <div style="border-top:1px solid var(--border); padding-top:.875rem;">
            <div class="section-title" style="margin-bottom:.75rem;">Text Recognition (OCR)</div>

            <!-- Engine + source + psm row -->
            <div style="display:flex; flex-wrap:wrap; align-items:center; gap:.5rem; margin-bottom:.625rem;">
              <select v-model="ocrEngine[c.id]" style="width:auto; min-width:120px;">
                <option value="tesseract">Tesseract</option>
                <option value="gemini">Gemini AI</option>
              </select>
              <select v-model="ocrSource[c.id]" style="width:auto; min-width:130px;">
                <option value="original">Original image</option>
                <option value="cleaned">Cleaned image</option>
                <option value="threshold" :disabled="ocrEngine[c.id] === 'gemini'">OCR-optimized</option>
              </select>
              <select v-model="ocrPsm[c.id]" :disabled="ocrEngine[c.id] === 'gemini'" :style="'width:auto; min-width:150px; opacity:' + (ocrEngine[c.id] === 'gemini' ? 0.45 : 1) + ';'">
                <option :value="6">Single block (PSM 6)</option>
                <option :value="11">Sparse text (PSM 11)</option>
                <option :value="3">Auto (PSM 3)</option>
              </select>
              <button class="btn btn-primary btn-sm" @click="runOcr(c)" :disabled="ocrRunning[c.id]">
                <span v-if="ocrRunning[c.id]" class="spinner" style="width:12px;height:12px;border-width:2px;"></span>
                {{ ocrRunning[c.id] ? 'Running OCR…' : 'Run OCR' }}
              </button>
            </div>

            <!-- Advanced options (Tesseract only) -->
            <div v-if="ocrEngine[c.id] !== 'gemini'" style="display:flex; flex-wrap:wrap; gap:.75rem 1.25rem; margin-bottom:.625rem;">
              <label style="display:flex; align-items:center; gap:.375rem; font-size:.8125rem; color:var(--muted); cursor:pointer;">
                <input type="checkbox" v-model="ocrCrop[c.id]" style="width:14px;height:14px; accent-color:var(--accent); cursor:pointer;" />
                Crop to board first
              </label>
              <label style="display:flex; align-items:center; gap:.375rem; font-size:.8125rem; color:var(--muted);">
                Noise filter:
                <select v-model.number="ocrMinConf[c.id]" style="width:auto; min-width:110px; padding:.25rem .5rem;">
                  <option :value="0">Off</option>
                  <option :value="30">Light (30)</option>
                  <option :value="40">Medium (40)</option>
                </select>
              </label>
              <label style="display:flex; align-items:center; gap:.375rem; font-size:.8125rem; color:var(--muted);">
                Filter type:
                <select v-model="ocrFilter[c.id]" style="width:auto; min-width:110px; padding:.25rem .5rem;">
                  <option value="line">Whole lines</option>
                  <option value="word">Single words</option>
                </select>
              </label>
            </div>

            <!-- OCR result feedback -->
            <div v-if="ocrErr[c.id]" class="alert alert-error" style="margin-bottom:.5rem;">{{ ocrErr[c.id] }}</div>
            <div v-if="ocrMsg[c.id]" class="alert alert-success" style="margin-bottom:.5rem;">{{ ocrMsg[c.id] }}</div>

            <div v-if="ocrEngine[c.id] !== 'gemini'" style="display:flex; flex-wrap:wrap; gap:.5rem 1rem; margin-bottom:.5rem;">
              <span v-if="ocrCropped[c.id] === true"  style="font-size:.75rem; color:var(--muted);">✓ Cropped to board</span>
              <span v-if="ocrCropped[c.id] === false" style="font-size:.75rem; color:var(--warning);">Board not found — full image used</span>
              <span v-if="ocrWordsDropped[c.id] > 0" style="font-size:.75rem; color:var(--muted);">{{ ocrWordsDropped[c.id] }} words filtered</span>
              <span v-if="ocrLinesDropped[c.id] > 0" style="font-size:.75rem; color:var(--muted);">{{ ocrLinesDropped[c.id] }} lines filtered</span>
              <span v-if="typeof ocrConfidence[c.id] === 'number'" style="font-size:.75rem; color:var(--muted);">Confidence: {{ Math.round(ocrConfidence[c.id]) }}%</span>
              <span v-if="typeof ocrMs[c.id] === 'number'" style="font-size:.75rem; color:var(--muted);">Time: {{ ocrMs[c.id] }} ms</span>
            </div>

            <!-- Extracted text textarea -->
            <div style="position:relative; margin-bottom:.625rem;">
              <label style="font-size:.75rem; font-weight:500; color:var(--muted); margin-bottom:.375rem; display:block;">Extracted text <span style="font-weight:400;">(review and edit before saving)</span></label>
              <textarea
                v-model="extractedDrafts[c.id]"
                rows="5"
                placeholder="Run OCR to extract text, or type manually…"
                style="font-family:monospace; font-size:.8125rem; line-height:1.7; resize:vertical;"
              ></textarea>
            </div>

            <!-- Action buttons -->
            <div style="display:flex; align-items:center; gap:.5rem; flex-wrap:wrap;">
              <button class="btn btn-primary btn-sm" @click="saveExtracted(c)">Save text</button>
              <button class="btn btn-secondary btn-sm" @click="copyText(c.id)" :disabled="!extractedDrafts[c.id]">
                {{ copiedId === c.id ? '✓ Copied' : 'Copy text' }}
              </button>
              <button class="btn btn-secondary btn-sm" @click="cleanCapture(c)" :disabled="cleaning[c.id]">
                <span v-if="cleaning[c.id]" class="spinner" style="width:12px;height:12px;border-width:2px;"></span>
                {{ cleaning[c.id] ? 'Cleaning…' : c.cleaned_image ? 'Clean again' : 'Clean image' }}
              </button>
              <button class="btn btn-ghost btn-sm" @click="deleteCapture(c)" style="color:var(--danger); margin-left:auto;">Delete</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Lightbox -->
    <div v-if="enlarged" class="overlay" @click="enlarged = null">
      <img :src="enlarged" style="max-width:95vw; max-height:90vh; border-radius:.5rem; box-shadow:0 20px 60px rgba(0,0,0,.6);" />
    </div>
  </div>
</template>