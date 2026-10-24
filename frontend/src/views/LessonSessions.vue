<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Plus, Edit2, Trash2 } from 'lucide-vue-next'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'
const router = useRouter()

const sessions = ref([])
const courses = ref([])
const search = ref('')
const courseFilter = ref('')
const statusFilter = ref('')
const loading = ref(false)
const error = ref('')
const showModal = ref(false)
const modalMode = ref('add')
const form = ref({ id: null, course: '', title: '', date: '', status: 'draft', notes: '' })
const formError = ref('')

const statusColors = {
  draft: 'bg-slate-700 text-slate-200',
  capturing: 'bg-yellow-900 text-yellow-300',
  processing: 'bg-blue-900 text-blue-300',
  finalized: 'bg-green-900 text-green-300'
}

async function loadAllCourses() {
  let all = []
  let url = API_BASE + '/courses/'
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
  courses.value = all
}

function buildQuery() {
  const params = []
  if (search.value) params.push('search=' + encodeURIComponent(search.value))
  if (courseFilter.value) params.push('course=' + encodeURIComponent(courseFilter.value))
  if (statusFilter.value) params.push('status=' + encodeURIComponent(statusFilter.value))
  return params.length ? '?' + params.join('&') : ''
}

async function fetchSessions() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(API_BASE + '/sessions/' + buildQuery())
    if (!res.ok) throw new Error('API ' + res.status)
    const data = await res.json()
    sessions.value = Array.isArray(data) ? data : (data.results || [])
  } catch (e) {
    error.value = 'Failed to load sessions. Is the API running?'
    sessions.value = []
  } finally {
    loading.value = false
  }
}

function openAdd() {
  modalMode.value = 'add'
  form.value = { id: null, course: courses.value[0]?.id || '', title: '', date: '', status: 'draft', notes: '' }
  formError.value = ''
  showModal.value = true
}

function openEdit(s) {
  modalMode.value = 'edit'
  form.value = { id: s.id, course: s.course, title: s.title || '', date: s.date || '', status: s.status || 'draft', notes: s.notes || '' }
  formError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

function validate() {
  if (!form.value.course) return 'Course is required'
  if (!form.value.title || !form.value.title.trim()) return 'Title is required'
  if (!form.value.date) return 'Date is required'
  return ''
}

async function saveSession() {
  formError.value = validate()
  if (formError.value) return
  try {
    if (modalMode.value === 'add') {
      const res = await fetch(API_BASE + '/sessions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          course: form.value.course,
          title: form.value.title.trim(),
          date: form.value.date,
          status: form.value.status,
          notes: form.value.notes || ''
        })
      })
      if (!res.ok) throw new Error('Failed')
    } else {
      const res = await fetch(API_BASE + '/sessions/' + form.value.id + '/', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          course: form.value.course,
          title: form.value.title.trim(),
          date: form.value.date,
          status: form.value.status,
          notes: form.value.notes || ''
        })
      })
      if (!res.ok) throw new Error('Failed')
    }
    closeModal()
    await fetchSessions()
  } catch (e) {
    formError.value = 'Failed to save session'
  }
}

async function deleteSession(s) {
  if (!confirm("This also deletes this session's captures and PDFs.")) return
  try {
    const res = await fetch(API_BASE + '/sessions/' + s.id + '/', { method: 'DELETE' })
    if (res.ok || res.status === 204) {
      await fetchSessions()
    } else {
      throw new Error('Failed')
    }
  } catch (e) {
    error.value = 'Failed to delete session'
  }
}

function goDetail(s) {
  router.push('/sessions/' + s.id)
}

function onFilter() {
  fetchSessions()
}

onMounted(async () => {
  await loadAllCourses()
  await fetchSessions()
})
</script>

<template>
  <div class="p-4">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-semibold text-cyan-400">Lesson Sessions</h1>
      <button @click="openAdd" :disabled="courses.length === 0" class="flex items-center gap-2 px-3 py-2 bg-cyan-400 text-black rounded hover:opacity-90 disabled:opacity-50">
        <Plus class="w-4 h-4" /> New Session
      </button>
    </div>

    <div v-if="courses.length === 0" class="mb-4 p-3 bg-yellow-900/40 border border-yellow-700 rounded text-yellow-300">
      Create a course first <router-link to="/courses" class="underline">here</router-link>
    </div>

    <div class="mb-4 flex flex-wrap items-center gap-2">
      <div class="relative w-full max-w-xs">
        <Search class="absolute left-2 top-2.5 w-4 h-4 text-slate-400" />
        <input v-model="search" @input="onFilter" placeholder="Search by title" class="w-full pl-8 pr-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-200" />
      </div>
      <select v-model="courseFilter" @change="onFilter" class="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-200">
        <option value="">All Courses</option>
        <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.code }} - {{ c.name }}</option>
      </select>
      <select v-model="statusFilter" @change="onFilter" class="px-3 py-2 bg-slate-900 border border-slate-700 rounded text-slate-200">
        <option value="">All Status</option>
        <option value="draft">Draft</option>
        <option value="capturing">Capturing</option>
        <option value="processing">Processing</option>
        <option value="finalized">Finalized</option>
      </select>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-900/40 border border-red-700 rounded text-red-300">{{ error }}</div>

    <div v-if="loading" class="text-slate-400">Loading...</div>

    <div v-else-if="sessions.length === 0" class="card p-6 text-center">
      <p class="text-slate-400 mb-3">No lesson sessions yet</p>
      <button @click="openAdd" :disabled="courses.length === 0" class="px-3 py-2 bg-cyan-400 text-black rounded disabled:opacity-50">New Session</button>
    </div>

    <div v-else class="overflow-x-auto card">
      <table class="w-full">
        <thead>
          <tr class="border-b border-slate-700">
            <th class="text-left p-3 text-slate-300">Title</th>
            <th class="text-left p-3 text-slate-300">Course</th>
            <th class="text-left p-3 text-slate-300">Date</th>
            <th class="text-left p-3 text-slate-300">Status</th>
            <th class="text-left p-3 text-slate-300">Captures</th>
            <th class="text-left p-3 text-slate-300">PDFs</th>
            <th class="text-right p-3 text-slate-300">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sessions" :key="s.id" class="border-b border-slate-800 hover:bg-slate-900/50">
            <td class="p-3 text-cyan-300 cursor-pointer hover:underline" @click="goDetail(s)">
              {{ s.title }}
              <span v-if="s.title && s.title.indexOf('[Sample]') === 0" class="ml-2 px-2 py-0.5 text-xs rounded bg-cyan-900 text-cyan-300">Sample</span>
            </td>
            <td class="p-3 text-slate-200">{{ s.course_code }} - {{ s.course_name }}</td>
            <td class="p-3 text-slate-400">{{ s.date }}</td>
            <td class="p-3"><span :class="statusColors[s.status] || 'px-2 py-0.5 rounded text-xs'">{{ s.status }}</span></td>
            <td class="p-3 text-slate-400">{{ s.capture_count }}</td>
            <td class="p-3 text-slate-400">{{ s.pdf_count }}</td>
            <td class="p-3 text-right flex items-center justify-end gap-2">
              <button @click="openEdit(s)" class="p-2 hover:bg-slate-800 rounded"><Edit2 class="w-4 h-4" /></button>
              <button @click="deleteSession(s)" class="p-2 hover:bg-red-900/40 text-red-400 rounded"><Trash2 class="w-4 h-4" /></button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div class="bg-slate-900 border border-slate-700 rounded-lg w-full max-w-md p-4">
        <h2 class="text-lg font-semibold text-cyan-400 mb-3">{{ modalMode === 'add' ? 'New Session' : 'Edit Session' }}</h2>
        <div class="space-y-3">
          <div>
            <label class="block text-sm text-slate-300 mb-1">Course *</label>
            <select v-model="form.course" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200">
              <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.code }} - {{ c.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-slate-300 mb-1">Title *</label>
            <input v-model="form.title" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200" />
          </div>
          <div>
            <label class="block text-sm text-slate-300 mb-1">Date *</label>
            <input type="date" v-model="form.date" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200" />
          </div>
          <div>
            <label class="block text-sm text-slate-300 mb-1">Status</label>
            <select v-model="form.status" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200">
              <option value="draft">Draft</option>
              <option value="capturing">Capturing</option>
              <option value="processing">Processing</option>
              <option value="finalized">Finalized</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-slate-300 mb-1">Notes</label>
            <textarea v-model="form.notes" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200"></textarea>
          </div>
          <div v-if="formError" class="text-red-400 text-sm">{{ formError }}</div>
        </div>
        <div class="flex justify-end gap-2 mt-4">
          <button @click="closeModal" class="px-3 py-2 bg-slate-700 text-slate-200 rounded">Cancel</button>
          <button @click="saveSession" class="px-3 py-2 bg-cyan-400 text-black rounded">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>