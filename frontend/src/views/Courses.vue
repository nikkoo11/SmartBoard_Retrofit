<script setup>
import { ref, onMounted } from 'vue'
import { Search, Plus, Edit2, Trash2 } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const selectedDays = ref([])
const startTime = ref('')
const endTime = ref('')
const oldSchedule = ref('')

const courses = ref([])
const search = ref('')
const loading = ref(false)
const error = ref('')
const showModal = ref(false)
const modalMode = ref('add')
const form = ref({ id: null, code: '', name: '', section: '', schedule: '' })
const formError = ref('')

function toggleDay(d) {
  const idx = selectedDays.value.indexOf(d)
  if (idx >= 0) {
    selectedDays.value.splice(idx, 1)
  } else {
    selectedDays.value.push(d)
  }
}

function parseSchedule(s) {
  selectedDays.value = []
  startTime.value = ''
  endTime.value = ''
  oldSchedule.value = ''
  if (!s) return
  // Try to match: "Mon/Wed 09:00 - 10:30"
  const m = s.match(/([A-Za-z\/]+)\s+([0-9]{2}:[0-9]{2})\s*-\s*([0-9]{2}:[0-9]{2})/)
  if (m) {
    const dayStr = m[1]
    dayStr.split('/').forEach(d => {
      const dd = d.trim()
      if (days.includes(dd)) selectedDays.value.push(dd)
    })
    startTime.value = m[2]
    endTime.value = m[3]
    return
  }
  oldSchedule.value = s
}

function buildSchedule() {
  if (selectedDays.value.length === 0) return ''
  // validate times
  if (!startTime.value || !endTime.value) throw new Error('Both start and end times required')
  if (endTime.value <= startTime.value) throw new Error('End time must be later than start time')
  const dayStr = selectedDays.value.join('/')
  return dayStr + ' ' + startTime.value + ' - ' + endTime.value
}

async function fetchCourses() {
  loading.value = true
  error.value = ''
  try {
    const url = search.value ? API_BASE + '/courses/?search=' + encodeURIComponent(search.value) : API_BASE + '/courses/'
    const res = await fetch(url)
    if (!res.ok) throw new Error('API ' + res.status)
    const data = await res.json()
    courses.value = Array.isArray(data) ? data : (data.results || [])
  } catch (e) {
    error.value = 'Failed to load courses. Is the API running?'
    courses.value = []
  } finally {
    loading.value = false
  }
}

function openAdd() {
  modalMode.value = 'add'
  form.value = { id: null, code: '', name: '', section: '', schedule: '' }
  selectedDays.value = []
  startTime.value = ''
  endTime.value = ''
  oldSchedule.value = ''
  formError.value = ''
  showModal.value = true
}

function openEdit(c) {
  modalMode.value = 'edit'
  form.value = { id: c.id, code: c.code || '', name: c.name || '', section: c.section || '', schedule: c.schedule || '' }
  parseSchedule(c.schedule || '')
  formError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

function validate() {
  if (!form.value.code || !form.value.code.trim()) return 'Code is required'
  if (!form.value.name || !form.value.name.trim()) return 'Name is required'
  try {
    if (selectedDays.value.length > 0) {
      if (!startTime.value || !endTime.value) return 'Both start and end times required'
      if (endTime.value <= startTime.value) return 'End time must be later than start time'
    }
    return ''
  } catch (e) {
    return e.message
  }
}

async function saveCourse() {
  formError.value = validate()
  if (formError.value) return
  try {
    let scheduleToSend = ''
    if (selectedDays.value.length > 0) {
      const dayStr = selectedDays.value.join('/')
      scheduleToSend = dayStr + ' ' + startTime.value + ' - ' + endTime.value
    } else {
      scheduleToSend = ''
    }
    if (modalMode.value === 'add') {
      const res = await fetch(API_BASE + '/courses/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: form.value.code.trim(),
          name: form.value.name.trim(),
          section: form.value.section ? form.value.section.trim() : '',
          schedule: scheduleToSend
        })
      })
      if (!res.ok) throw new Error('Failed')
    } else {
      const res = await fetch(API_BASE + '/courses/' + form.value.id + '/', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: form.value.code.trim(),
          name: form.value.name.trim(),
          section: form.value.section ? form.value.section.trim() : '',
          schedule: scheduleToSend
        })
      })
      if (!res.ok) throw new Error('Failed')
    }
    closeModal()
    await fetchCourses()
  } catch (e) {
    formError.value = 'Failed to save course'
  }
}

async function deleteCourse(c) {
  if (!confirm('Delete course ' + c.code + '?')) return
  try {
    const res = await fetch(API_BASE + '/courses/' + c.id + '/', { method: 'DELETE' })
    if (res.ok || res.status === 204) {
      await fetchCourses()
    } else {
      throw new Error('Failed')
    }
  } catch (e) {
    error.value = 'Failed to delete course'
  }
}

function onSearch() {
  fetchCourses()
}

onMounted(fetchCourses)
</script>

<template>
  <div class="p-4">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-semibold text-cyan-400">Courses</h1>
      <button @click="openAdd" class="flex items-center gap-2 px-3 py-2 bg-cyan-400 text-black rounded hover:opacity-90">
        <Plus class="w-4 h-4" /> Add Course
      </button>
    </div>

    <div class="mb-4 flex items-center gap-2">
      <div class="relative w-full max-w-sm">
        <Search class="absolute left-2 top-2.5 w-4 h-4 text-slate-400" />
        <input v-model="search" @input="onSearch" placeholder="Search courses" class="w-full pl-8 pr-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-200" />
      </div>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-900/40 border border-red-700 rounded text-red-300">{{ error }}</div>

    <div v-if="loading" class="text-slate-400">Loading...</div>

    <div v-else-if="courses.length === 0" class="card p-6 text-center">
      <p class="text-slate-400 mb-3">No courses yet</p>
      <button @click="openAdd" class="px-3 py-2 bg-cyan-400 text-black rounded">Add Course</button>
    </div>

    <div v-else class="overflow-x-auto card">
      <table class="w-full">
        <thead>
          <tr class="border-b border-slate-700">
            <th class="text-left p-3 text-slate-300">Code</th>
            <th class="text-left p-3 text-slate-300">Name</th>
            <th class="text-left p-3 text-slate-300">Section</th>
            <th class="text-left p-3 text-slate-300">Schedule</th>
            <th class="text-right p-3 text-slate-300">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in courses" :key="c.id" class="border-b border-slate-800 hover:bg-slate-900/50">
            <td class="p-3 text-slate-200">{{ c.code }}</td>
            <td class="p-3 text-slate-200">
              {{ c.name }}
              <span v-if="c.name && c.name.indexOf('[Sample]') === 0" class="ml-2 px-2 py-0.5 text-xs rounded bg-cyan-900 text-cyan-300">Sample</span>
            </td>
            <td class="p-3 text-slate-400">{{ c.section }}</td>
            <td class="p-3 text-slate-400">{{ c.schedule }}</td>
            <td class="p-3 text-right flex items-center justify-end gap-2">
              <button @click="openEdit(c)" class="p-2 hover:bg-slate-800 rounded"><Edit2 class="w-4 h-4" /></button>
              <button @click="deleteCourse(c)" class="p-2 hover:bg-red-900/40 text-red-400 rounded"><Trash2 class="w-4 h-4" /></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div class="bg-slate-900 border border-slate-700 rounded-lg w-full max-w-md p-4">
        <h2 class="text-lg font-semibold text-cyan-400 mb-3">{{ modalMode === 'add' ? 'Add Course' : 'Edit Course' }}</h2>
        <div class="space-y-3">
          <div>
            <label class="block text-sm text-slate-300 mb-1">Code *</label>
            <input v-model="form.code" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200" />
          </div>
          <div>
            <label class="block text-sm text-slate-300 mb-1">Name *</label>
            <input v-model="form.name" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200" />
          </div>
          <div>
            <label class="block text-sm text-slate-300 mb-1">Section</label>
            <input v-model="form.section" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200" />
          </div>
          <div>
            <label class="block text-sm text-slate-300 mb-1">Schedule</label>
            <div class="flex flex-wrap gap-2 mb-2">
              <button v-for="d in days" :key="d" type="button" @click="toggleDay(d)" :class="selectedDays.includes(d) ? 'px-2 py-1 rounded bg-cyan-400 text-black' : 'px-2 py-1 rounded bg-slate-800 text-slate-200'">{{ d }}</button>
            </div>
            <div class="flex items-center gap-2 mb-2">
              <input type="time" v-model="startTime" class="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200" />
              <span class="text-slate-400">-</span>
              <input type="time" v-model="endTime" class="px-2 py-1 bg-slate-950 border border-slate-700 rounded text-slate-200" />
            </div>
            <div v-if="oldSchedule" class="text-xs text-slate-400">Current: {{ oldSchedule }}</div>
          </div>
          <div v-if="formError" class="text-red-400 text-sm">{{ formError }}</div>
        </div>
        <div class="flex justify-end gap-2 mt-4">
          <button @click="closeModal" class="px-3 py-2 bg-slate-700 text-slate-200 rounded">Cancel</button>
          <button @click="saveCourse" class="px-3 py-2 bg-cyan-400 text-black rounded">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>