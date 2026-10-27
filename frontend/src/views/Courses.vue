<script setup>
import { ref, onMounted } from 'vue'
import { Search, Plus, Edit2, Trash2 } from 'lucide-vue-next'
import { api } from '../services/api.js'

const days         = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const selectedDays = ref([])
const startTime    = ref('')
const endTime      = ref('')
const oldSchedule  = ref('')

const courses    = ref([])
const search     = ref('')
const loading    = ref(false)
const error      = ref('')
const showModal  = ref(false)
const modalMode  = ref('add')
const form       = ref({ id: null, code: '', name: '', section: '', schedule: '' })
const formError  = ref('')

function toggleDay(d) {
  const idx = selectedDays.value.indexOf(d)
  idx >= 0 ? selectedDays.value.splice(idx, 1) : selectedDays.value.push(d)
}

function parseSchedule(s) {
  selectedDays.value = []; startTime.value = ''; endTime.value = ''; oldSchedule.value = ''
  if (!s) return
  const m = s.match(/([A-Za-z\/]+)\s+([0-9]{2}:[0-9]{2})\s*-\s*([0-9]{2}:[0-9]{2})/)
  if (m) {
    m[1].split('/').forEach(d => { const dd = d.trim(); if (days.includes(dd)) selectedDays.value.push(dd) })
    startTime.value = m[2]; endTime.value = m[3]; return
  }
  oldSchedule.value = s
}

async function fetchCourses() {
  loading.value = true; error.value = ''
  try {
    const data = await api.courses(search.value)
    courses.value = Array.isArray(data) ? data : (data?.results || [])
  } catch {
    error.value = 'Failed to load courses. Is the API running?'
    courses.value = []
  } finally { loading.value = false }
}

function openAdd() {
  modalMode.value = 'add'; form.value = { id: null, code: '', name: '', section: '', schedule: '' }
  selectedDays.value = []; startTime.value = ''; endTime.value = ''; oldSchedule.value = ''
  formError.value = ''; showModal.value = true
}

function openEdit(c) {
  modalMode.value = 'edit'
  form.value = { id: c.id, code: c.code||'', name: c.name||'', section: c.section||'', schedule: c.schedule||'' }
  parseSchedule(c.schedule||''); formError.value = ''; showModal.value = true
}

function closeModal() { showModal.value = false }

function validate() {
  if (!form.value.code?.trim()) return 'Code is required'
  if (!form.value.name?.trim()) return 'Name is required'
  if (selectedDays.value.length > 0) {
    if (!startTime.value || !endTime.value) return 'Both start and end times required'
    if (endTime.value <= startTime.value) return 'End time must be later than start time'
  }
  return ''
}

async function saveCourse() {
  formError.value = validate(); if (formError.value) return
  try {
    let scheduleToSend = selectedDays.value.length > 0 ? selectedDays.value.join('/') + ' ' + startTime.value + ' - ' + endTime.value : ''
    const payload = { code: form.value.code.trim(), name: form.value.name.trim(), section: form.value.section?.trim()||'', schedule: scheduleToSend }
    if (modalMode.value === 'add') {
      await api.createCourse(payload)
    } else {
      await api.updateCourse(form.value.id, payload)
    }
    closeModal(); await fetchCourses()
  } catch { formError.value = 'Failed to save course' }
}

async function deleteCourse(c) {
  if (!confirm('Delete course ' + c.code + '?')) return
  try {
    await api.deleteCourse(c.id)
    await fetchCourses()
  } catch { error.value = 'Failed to delete course' }
}

onMounted(fetchCourses)
</script>

<template>
  <div>
    <div class="page-header flex items-center justify-between">
      <div>
        <h1>Courses</h1>
        <p>Manage your courses and schedules.</p>
      </div>
      <button class="btn btn-primary" @click="openAdd">
        <Plus style="width:15px;height:15px;" /> Add Course
      </button>
    </div>

    <!-- Search -->
    <div class="mb-4" style="max-width:360px; position:relative;">
      <Search style="position:absolute;left:.625rem;top:50%;transform:translateY(-50%);width:15px;height:15px;color:var(--muted);pointer-events:none;" />
      <input v-model="search" @input="fetchCourses" placeholder="Search courses…" style="padding-left:2.1rem;" />
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <div v-if="loading" class="flex items-center gap-2" style="color:var(--muted); font-size:.875rem; margin-bottom:1rem;">
      <span class="spinner"></span> Loading courses…
    </div>

    <div v-else-if="courses.length === 0" class="card">
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
        <span>No courses yet. Add your first course to get started.</span>
        <button class="btn btn-primary btn-sm" @click="openAdd"><Plus style="width:14px;height:14px;"/>Add Course</button>
      </div>
    </div>

    <div v-else class="card" style="padding:0; overflow:hidden;">
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Section</th>
              <th>Schedule</th>
              <th style="text-align:right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in courses" :key="c.id">
              <td style="font-weight:600; color:var(--text);">{{ c.code }}</td>
              <td style="color:var(--text);">
                {{ c.name }}
                <span v-if="c.name && c.name.startsWith('[Sample]')" style="margin-left:.4rem;" class="badge badge-processing">Sample</span>
              </td>
              <td style="color:var(--muted);">{{ c.section || '—' }}</td>
              <td style="color:var(--muted);">{{ c.schedule || '—' }}</td>
              <td style="text-align:right;">
                <div style="display:inline-flex; align-items:center; gap:.25rem;">
                  <button class="btn btn-ghost" @click="openEdit(c)" title="Edit"><Edit2 style="width:15px;height:15px;" /></button>
                  <button class="btn btn-ghost" @click="deleteCourse(c)" title="Delete" style="color:var(--danger);"><Trash2 style="width:15px;height:15px;" /></button>
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
          <h2>{{ modalMode === 'add' ? 'Add Course' : 'Edit Course' }}</h2>
          <button class="btn btn-ghost" @click="closeModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div style="display:flex; flex-direction:column; gap:.875rem;">
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.375rem; color:var(--muted);">Course Code <span style="color:var(--danger);">*</span></label>
            <input v-model="form.code" placeholder="e.g. ECE101" />
          </div>
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.375rem; color:var(--muted);">Course Name <span style="color:var(--danger);">*</span></label>
            <input v-model="form.name" placeholder="e.g. Signals and Systems" />
          </div>
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.375rem; color:var(--muted);">Section</label>
            <input v-model="form.section" placeholder="e.g. A1" />
          </div>
          <div>
            <label style="display:block; font-size:.8125rem; font-weight:500; margin-bottom:.5rem; color:var(--muted);">Schedule</label>
            <div style="display:flex; flex-wrap:wrap; gap:.375rem; margin-bottom:.625rem;">
              <button v-for="d in days" :key="d" type="button" @click="toggleDay(d)"
                :style="selectedDays.includes(d) ? 'background:var(--accent);color:#fff;border:none;border-radius:.375rem;padding:.3rem .6rem;font-size:.8rem;font-weight:600;' : 'background:var(--panel2);color:var(--muted);border:1px solid var(--border);border-radius:.375rem;padding:.3rem .6rem;font-size:.8rem;'">
                {{ d }}
              </button>
            </div>
            <div style="display:flex; align-items:center; gap:.5rem;">
              <input type="time" v-model="startTime" style="flex:1;" />
              <span style="color:var(--muted);">–</span>
              <input type="time" v-model="endTime" style="flex:1;" />
            </div>
            <div v-if="oldSchedule" style="font-size:.75rem; color:var(--muted); margin-top:.375rem;">Current: {{ oldSchedule }}</div>
          </div>
          <div v-if="formError" class="alert alert-error" style="margin-bottom:0;">{{ formError }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeModal">Cancel</button>
          <button class="btn btn-primary" @click="saveCourse">{{ modalMode === 'add' ? 'Add Course' : 'Save Changes' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
