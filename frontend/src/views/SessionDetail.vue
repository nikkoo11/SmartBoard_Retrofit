<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../services/api.js'

const route    = useRoute()
const id       = route.params.id

const session  = ref(null)
const captures = ref([])
const pdfs     = ref([])
const loading  = ref(false)
const error    = ref('')
const enlarged = ref(null)

const statusLabels = { draft:'Draft', capturing:'Capturing', processing:'Processing', finalized:'Finalized' }

async function fetchData() {
  loading.value = true; error.value = ''
  try {
    try { session.value = await api.session(id) } catch { error.value = 'Failed to load session' }
    try {
      const cd = await api.captures('?session=' + id)
      captures.value = Array.isArray(cd) ? cd : (cd.results || [])
    } catch {}
    try {
      const pd = await api.pdfs('?session=' + id)
      pdfs.value = Array.isArray(pd) ? pd : (pd.results || [])
    } catch {}
  } catch { error.value = 'Failed to load session details' }
  finally { loading.value = false }
}

function formatDate(s) {
  if (!s) return '—'
  try { return new Date(s).toLocaleDateString(undefined, { year:'numeric', month:'short', day:'numeric' }) } catch { return s }
}

function pdfFilename(url) {
  try { return decodeURIComponent(url.split('/').pop().split('?')[0]) } catch { return 'PDF' }
}

onMounted(fetchData)
</script>

<template>
  <div>
    <!-- Breadcrumb -->
    <nav style="display:flex; align-items:center; gap:.5rem; font-size:.8125rem; color:var(--muted); margin-bottom:1rem;">
      <router-link to="/sessions" style="color:var(--muted);">Lesson Sessions</router-link>
      <span>›</span>
      <span style="color:var(--text);">{{ session ? session.title : 'Session Detail' }}</span>
    </nav>

    <div class="page-header flex items-center justify-between">
      <div>
        <h1>{{ session ? session.title : 'Session Detail' }}</h1>
        <p v-if="session">{{ session.course_code }} – {{ session.course_name }} · {{ session.date }}</p>
      </div>
      <router-link :to="'/capture?session=' + id" class="btn btn-primary btn-sm">Open in Capture →</router-link>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="flex items-center gap-2" style="color:var(--muted); font-size:.875rem; margin-bottom:1rem;">
      <span class="spinner"></span> Loading…
    </div>

    <!-- Session info card -->
    <div v-if="session" class="card mb-4">
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:1.25rem;">
        <div>
          <div class="section-title">Course</div>
          <div style="font-size:.9375rem; font-weight:500;">{{ session.course_code }} – {{ session.course_name }}</div>
        </div>
        <div>
          <div class="section-title">Date</div>
          <div style="font-size:.9375rem;">{{ session.date }}</div>
        </div>
        <div>
          <div class="section-title">Status</div>
          <span :class="'badge badge-' + session.status">{{ statusLabels[session.status] || session.status }}</span>
        </div>
        <div v-if="session.notes" style="grid-column:1/-1;">
          <div class="section-title">Notes</div>
          <div style="white-space:pre-wrap; font-size:.875rem; color:var(--muted);">{{ session.notes }}</div>
        </div>
      </div>
    </div>

    <!-- Captures -->
    <div class="mb-4">
      <h2 style="font-size:1rem; margin-bottom:.875rem;">
        Captures
        <span style="font-size:.8rem; font-weight:400; color:var(--muted); margin-left:.5rem;">{{ captures.length }}</span>
      </h2>
      <div v-if="captures.length === 0" class="card">
        <div class="empty-state" style="padding:1.5rem 1rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          <span>No captures yet. <router-link :to="'/capture?session=' + id">Open Whiteboard Capture</router-link> to add images.</span>
        </div>
      </div>
      <div v-else style="display:flex; flex-direction:column; gap:.875rem;">
        <div v-for="cap in captures" :key="cap.id" class="card" style="padding:0; overflow:hidden;">
          <img
            v-if="cap.image"
            :src="cap.image"
            style="width:100%; max-height:320px; object-fit:contain; background:#000; cursor:zoom-in; display:block;"
            @click="enlarged = cap.image"
            alt="Board capture"
          />
          <div style="padding:1rem;">
            <div class="section-title">Extracted Text</div>
            <div v-if="cap.extracted_text && cap.extracted_text.trim()" style="white-space:pre-wrap; font-size:.875rem; font-family:monospace; background:var(--bg); border:1px solid var(--border); border-radius:.375rem; padding:.75rem; color:var(--text); line-height:1.7; margin-top:.375rem;">{{ cap.extracted_text }}</div>
            <div v-else style="font-size:.875rem; color:var(--muted); margin-top:.375rem; font-style:italic;">No text extracted yet. Run OCR in the Whiteboard Capture view.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- PDFs -->
    <div>
      <h2 style="font-size:1rem; margin-bottom:.875rem;">
        PDFs
        <span style="font-size:.8rem; font-weight:400; color:var(--muted); margin-left:.5rem;">{{ pdfs.length }}</span>
      </h2>
      <div v-if="pdfs.length === 0" class="card">
        <div class="empty-state" style="padding:1.5rem 1rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>No PDFs generated yet. Finalize the session from the Whiteboard Capture view.</span>
        </div>
      </div>
      <ul v-else style="margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:.5rem;">
        <li v-for="p in pdfs" :key="p.id" class="card" style="margin-bottom:0; display:flex; align-items:center; justify-content:space-between; gap:1rem;">
          <span style="font-size:.875rem; font-weight:500; color:var(--text);">{{ pdfFilename(p.file) }}</span>
          <div style="display:flex; align-items:center; gap:.5rem; flex-shrink:0;">
            <span style="font-size:.75rem; color:var(--muted);">{{ formatDate(p.created_at) }}</span>
            <a :href="p.file" target="_blank" class="btn btn-secondary btn-sm">View →</a>
          </div>
        </li>
      </ul>
    </div>

    <!-- Lightbox -->
    <div v-if="enlarged" class="overlay" @click="enlarged = null">
      <img :src="enlarged" style="max-width:95vw; max-height:90vh; border-radius:.5rem; box-shadow:0 20px 60px rgba(0,0,0,.6);" />
    </div>
  </div>
</template>
