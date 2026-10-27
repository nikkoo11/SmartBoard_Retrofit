<script setup>
import { ref, onMounted } from 'vue'
import { Search, FileText, Download, Trash2 } from 'lucide-vue-next'
import { api, request } from '../services/api.js'

const pdfs            = ref([])
const pdfNext         = ref(null)
const sessions        = ref([])
const sessionsNext    = ref(null)
const search          = ref('')
const loading         = ref(true)
const authError        = ref(false)
const error            = ref('')
const selectedSession = ref('')
const generating      = ref(false)
const genMsg          = ref('')
const genErr          = ref('')

const requestId       = ref(0)

async function fetchPdfs(append = false) {
  const current = ++requestId.value
  loading.value = true; error.value = ''; authError.value = false
  try {
    const url = search.value ? '/pdfs/?search=' + encodeURIComponent(search.value) : '/pdfs/'
    const data = await request(url)
    if (current !== requestId.value) return
    const items = Array.isArray(data) ? data : (data.results || [])
    pdfs.value = append ? pdfs.value.concat(items) : items
    pdfNext.value = (data && !Array.isArray(data)) ? data.next : null
  } catch (e) {
    if (current !== requestId.value) return
    if (e && e.status === 401) authError.value = true
    error.value = e && e.message ? e.message : 'Failed to load PDFs. Is the API running?'
    pdfNext.value = null
  } finally {
    if (current === requestId.value) loading.value = false
  }
}

async function loadMorePdfs() {
  if (!pdfNext.value || loading.value) return
  const current = requestId.value
  loading.value = true
  try {
    const data = await request(pdfNext.value)
    if (current !== requestId.value) return
    const items = Array.isArray(data) ? data : (data.results || [])
    pdfs.value = pdfs.value.concat(items)
    pdfNext.value = (data && !Array.isArray(data)) ? data.next : null
  } catch { error.value = 'Failed to load more PDFs.' }
  finally { if (current === requestId.value) loading.value = false }
}

async function fetchSessions() {
  try {
    const data = await request('/sessions/')
    sessions.value = Array.isArray(data) ? data : (data.results || [])
    sessionsNext.value = (data && !Array.isArray(data)) ? data.next : null
  } catch { sessions.value = [] }
}

async function generatePdf() {
  if (!selectedSession.value) return
  generating.value = true; genMsg.value = ''; genErr.value = ''
  try {
    await api.generatePdf(selectedSession.value)
    genMsg.value = 'PDF generated successfully.'
    try { await fetchPdfs() } catch {}
    error.value = ''
    authError.value = false
  } catch (e) {
    genErr.value = e.message || 'Failed to generate PDF'
  } finally { generating.value = false }
}

async function deletePdf(p) {
  if (!confirm('Delete this PDF?')) return
  try {
    await api.deletePdf(p.id)
    await fetchPdfs()
  } catch { error.value = 'Failed to delete PDF' }
}

function viewPdf(p)     { if (p.file) window.open(p.file, '_blank') }
function downloadPdf(p) {
  if (!p.file) return
  const a = document.createElement('a'); a.href = p.file; a.download = ''; a.target = '_blank'
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
}

function formatDate(s) {
  if (!s) return '—'
  try { return new Date(s).toLocaleDateString(undefined, { year:'numeric', month:'short', day:'numeric' }) } catch { return s }
}

onMounted(async () => { await fetchSessions(); await fetchPdfs() })
</script>

<template>
  <div>
    <div class="page-header">
      <h1>PDF Archive</h1>
      <p>View, download, and manage generated session PDFs.</p>
    </div>

    <!-- Generate PDF panel -->
    <div class="card mb-4">
      <div class="section-title">Generate PDF from session</div>
      <div style="display:flex; flex-wrap:wrap; align-items:center; gap:.625rem; margin-bottom:.625rem;">
        <select v-model="selectedSession" style="flex:1; min-width:200px; max-width:400px;">
          <option value="">Select a session…</option>
          <option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.course_code }} – {{ s.title }} ({{ s.date }})</option>
        </select>
        <button class="btn btn-primary" @click="generatePdf" :disabled="!selectedSession || generating">
          <span v-if="generating" class="spinner" style="width:14px;height:14px;border-width:2px;"></span>
          {{ generating ? 'Generating…' : 'Generate PDF' }}
        </button>
      </div>
      <div v-if="genMsg" class="alert alert-success" style="margin-bottom:0;">{{ genMsg }}</div>
      <div v-if="genErr" class="alert alert-error" style="margin-bottom:0;">{{ genErr }}</div>
    </div>

    <!-- Search -->
    <div style="position:relative; max-width:320px; margin-bottom:1.25rem;">
      <Search style="position:absolute;left:.625rem;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--muted);pointer-events:none;" />
      <input v-model="search" @input="fetchPdfs" placeholder="Search by session or course…" style="padding-left:2rem;" />
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="authError" class="alert alert-error">Please log in to view PDFs.</div>
    <div v-if="error || authError" style="margin-bottom:1rem;">
      <button class="btn btn-secondary btn-sm" @click="fetchPdfs" :disabled="loading">Retry</button>
    </div>

    <div v-if="loading" class="flex items-center gap-2" style="color:var(--muted); font-size:.875rem; margin-bottom:1rem;">
      <span class="spinner"></span> Loading PDFs…
    </div>

    <div v-else-if="!error && !authError && pdfs.length === 0" class="card">
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        <span>No PDFs yet. Generate one from a session that has captures with extracted text.</span>
      </div>
    </div>

    <div v-else class="card" style="padding:0; overflow:hidden;">
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>Course</th>
              <th>Session</th>
              <th>Created</th>
              <th style="text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in pdfs" :key="p.id">
              <td style="color:var(--text); font-weight:500;">{{ p.course_name || '—' }}</td>
              <td style="color:var(--muted);">{{ p.session_title || '—' }}</td>
              <td style="color:var(--muted); white-space:nowrap;">{{ formatDate(p.created_at) }}</td>
              <td style="text-align:right;">
                <div style="display:inline-flex; align-items:center; gap:.375rem;">
                  <button class="btn btn-secondary btn-sm" @click="viewPdf(p)">
                    <FileText style="width:13px;height:13px;" /> View
                  </button>
                  <button class="btn btn-secondary btn-sm" @click="downloadPdf(p)">
                    <Download style="width:13px;height:13px;" /> Download
                  </button>
                  <button class="btn btn-ghost" @click="deletePdf(p)" title="Delete" style="color:var(--danger);">
                    <Trash2 style="width:15px;height:15px;" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-if="pdfNext" style="margin-top:1rem;">
      <button class="btn btn-secondary btn-sm" @click="loadMorePdfs" :disabled="loading">Load more</button>
    </div>
  </div>
</template>
