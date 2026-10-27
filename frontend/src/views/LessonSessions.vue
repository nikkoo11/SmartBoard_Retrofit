<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Plus, Edit2, Trash2 } from 'lucide-vue-next'
import { api, request } from '../services/api.js'

const router = useRouter()

const sessions     = ref([])
const courses      = ref([])
const search       = ref('')
const courseFilter = ref('')
const statusFilter = ref('')
const loading      = ref(false)
const error        = ref('')
const showModal    = ref(false)
const modalMode    = ref('add')
const form         = ref({ id: null, course: '', title: '', date: '', status: 'draft', notes: '' })
const formError    = ref('')

async function loadAllCourses() {
  let all = [], url = '/courses/'
  while (url) {
    try {
      const data = await request(url)
      if (Array.isArray(data)) { all = all.concat(data); break }
      else if (data.results) { all = all.concat(data.results); url = data.next }
      else break
    } catch { break }
  }
  courses.value = all
}

function buildQuery() {
  const p = []
  if (search.value)       p.push('search=' + encodeURIComponent(search.value))
  if (courseFilter.value) p.push('course=' + encodeURIComponent(courseFilter.value))
  if (statusFilter.value) p.push('status=' + encodeURIComponent(statusFilter.value))
  return p.length ? '?' + p.join('&') : ''
}

async function fetchSessions() {
  loading.value = true; error.value = ''
  try {
    const data = await api.sessions(buildQuery())
    sessions.value = Array.isArray(data) ? data : (data.results || [])
  } catch {
    error.value = 'Failed to load sessions. Is the API running?'; sessions.value = []
  } finally { loading.value = false }
}

function openAdd() {
  modalMode.value = 'add'
  form.value = { id: null, course: courses.value[0]?.id || '', title: '', date: '', status: 'draft', notes: '' }
  formError.value = ''; showModal.value = true
}

function openEdit(s) {
  modalMode.value = 'edit'
  form.value = { id: s.id, course: s.course, title: s.title||'', date: s.date||'', status: s.status||'draft', notes: s.notes||'' }
  formError.value = ''; showModal.value = true
}

function closeModal() { showModal.value = false }

function validate() {
  if (!form.value.course) return 'Course is required'
  if (!form.value.title?.trim()) return 'Title is required'
  if (!form.value.date) return 'Date is required'
  return ''
}

async function saveSession() {
  formError.value = validate(); if (formError.value) return
  try {
    const data = { course: form.value.course, title: form.value.title.trim(), date: form.value.date, status: form.value.status, notes: form.value.notes || '' }
    if (modalMode.value === 'add') {
      await api.createSession(data)
    } else {
      await api.updateSession(form.value.id, data)
    }
    closeModal(); await fetchSessions()
  } catch { formError.value = 'Failed to save session' }
}

async function deleteSession(s) {
  if (!confirm("This also deletes this session's captures and PDFs. Continue?")) return
  try {
    await api.deleteSession(s.id)
    await fetchSessions()
  } catch { error.value = 'Failed to delete session' }
}

function goDetail(s) { router.push('/sessions/' + s.id) }
function onFilter()  { fetchSessions() }

onMounted(async () => { await loadAllCourses(); await fetchSessions() })
</script>

<template>
  <div>
    <div class="page-header flex items-center justify-between">
      <div>
        <h1>Lesson Sessions</h1>
        <p>Create and manage your class lesson sessions.</p>
      </div>
      <button class="btn btn-primary" @click="openAdd" :disabled="courses.length === 0">
        <Plus style="width:15px;height:15px;" /> New Session
      </button>
    </div>

    <div v-if="courses.length === 0" class="alert alert-warn">
      No courses found. <router-link to="/courses">Add a course</router-link> first.
    </div>

    <!-- Filters -->
    <div style="display:flex; flex-wrap:wrap; align-items:center; gap:.5rem; margin-bottom:1.25rem;">
      <div style="position:relative; flex:1; min-width:180px; max-width:280px;">
        <Search style="position:absolute;left:.625rem;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--muted);pointer-events:none;" />
        <input v-model="search" @input="onFilter" placeholder="Search by title…" style="padding-left:2rem;" />
      </div>
      <select v-model="courseFilter" @change="onFilter" style="flex:1; min-width:160px; max-width:240px;">
        <option value="">All Courses</option>
        <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.code }} – {{ c.name }}</option>
      </select>
      <select v-model="statusFilter" @change="onFilter" style="flex:1; min-width:120px; max-width:160px;">
        <option value="">All Status</option>
        <option value="draft">Draft</option>
        <option value="capturing">Capturing</option>
        <option value="processing">Processing</option>
        <option value="finalized">Finalized</option>
      </select>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <div v-if="loading" class="flex items-center gap-2" style="color:var(--muted); font-size:.875rem; margin-bottom:1rem;">
      <span class="spinner"></span> Loading sessions…
    </div>

    <div v-else-if="sessions.length === 0" class="card">
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        <span>No sessions found.</span>
        <button class="btn btn-primary btn-sm" @click="openAdd" :disabled="courses.length === 0"><Plus style="width:14px;height:14px;" />New Session</button>
      </div>
    </div>

    <div v-else class="card" style="padding:0; overflow:hidden;">
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Course</th>
              <th>Date</th>
              <th>Status</th>
              <th>Captures</th>
              <th>PDFs</th>
              <th style="text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sessions" :key="s.id" style="cursor:pointer;" @click="goDetail(s)">
              <td style="font-weight:500; color:var(--text);">
                {{ s.title }}
                <span v-if="s.title && s.title.startsWith('[Sample]')" style="margin-left:.4rem;" class="badge badge-processing">Sample</span>
              </td>
              <td style="color:var(--muted);">{{ s.course_code }} – {{ s.course_name }}</td>
              <td style="color:var(--muted);">{{ s.date }}</td>
              <td><span :class="'badge badge-' + s.status">{{ s.status }}</span></td>
              <td style="color:var(--muted);">{{ s.capture_count }}</td>
              <td style="color:var(--muted);">{{ s.pdf_count }}</td>
              <td style="text-align:right;" @click.stop>
                <div style="display:inline-flex; align-items:center; gap:.25rem;">
                  <button class="btn btn-ghost" @click="openEdit(s)" title="Edit"><Edit2 style="width:15px;height:15px;" /></button>
                  <button class="btn btn-ghost" @click="deleteSession(s)" title="Delete" style="color:var(--danger);"><Trash2 style="width:15px;height:15px;" /></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal -->
    <div v-if="showModal" class="overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ modalMode === 'add' ? 'New Session' : 'Edit Session' }}</h2>
          <button class="btn btn-ghost" @click="closeModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div style="display:flex; flex-direction:column; gap:.875rem;">
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.375rem; color:var(--muted);">Course <span style="color:var(--danger);">*</span></label>
            <select v-model="form.course">
              <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.code }} – {{ c.name }}</option>
            </select>
          </div>
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.375rem; color:var(--muted);">Title <span style="color:var(--danger);">*</span></label>
            <input v-model="form.title" placeholder="e.g. Introduction to Signals" />
          </div>
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.375rem; color:var(--muted);">Date <span style="color:var(--danger);">*</span></label>
            <input type="date" v-model="form.date" />
          </div>
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.375rem; color:var(--muted);">Status</label>
            <select v-model="form.status">
              <option value="draft">Draft</option>
              <option value="capturing">Capturing</option>
              <option value="processing">Processing</option>
              <option value="finalized">Finalized</option>
            </select>
          </div>
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.375rem; color:var(--muted);">Notes</label>
            <textarea v-model="form.notes" rows="3" placeholder="Optional notes…"></textarea>
          </div>
          <div v-if="formError" class="alert alert-error" style="margin-bottom:0;">{{ formError }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeModal">Cancel</button>
          <button class="btn btn-primary" @click="saveSession">{{ modalMode === 'add' ? 'Create Session' : 'Save Changes' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
