<script setup>
import { ref, onMounted } from 'vue'

const STORAGE_KEY = 'smartboard_settings'

const defaults = {
  name: '',
  role: 'Teacher',
  esp32Address: '',
  edgeComputerAddress: '',
  pageSize: 'A4',
  includeImages: true,
  emailEnabled: false
}

const form = ref({ ...defaults })
const savedMsg = ref('')
const testing = ref(false)
const testResult = ref('')

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      form.value = { ...defaults, ...parsed }
    } else {
      form.value = { ...defaults }
    }
  } catch (e) {
    form.value = { ...defaults }
  }
}

function save() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(form.value))
    savedMsg.value = 'Saved'
    setTimeout(() => { savedMsg.value = '' }, 2000)
  } catch (e) {
    // ignore
  }
}

function reset() {
  if (!confirm('Reset to defaults?')) return
  form.value = { ...defaults }
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch (e) {}
  savedMsg.value = 'Saved'
  setTimeout(() => { savedMsg.value = '' }, 2000)
}

function validateUrl(v) {
  if (!v) return true
  return v.startsWith('http://') || v.startsWith('https://')
}

async function testConnection() {
  testing.value = true
  testResult.value = ''
  try {
    const res = await fetch('http://127.0.0.1:8000/api/courses/')
    if (res.ok) {
      testResult.value = 'Connected'
    } else {
      testResult.value = 'Cannot reach the backend'
    }
  } catch (e) {
    testResult.value = 'Cannot reach the backend'
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="mb-4">
    <h1 class="text-2xl font-semibold text-cyan-400 mb-2">Settings</h1>
    <p class="text-slate-400 mb-4">Settings are saved in this browser only.</p>

    <div class="card mb-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-3">Profile</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label class="block text-sm text-slate-300 mb-1">Name</label>
          <input v-model="form.name" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200" />
        </div>
        <div>
          <label class="block text-sm text-slate-300 mb-1">Role</label>
          <select v-model="form.role" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200">
            <option>Teacher</option>
            <option>Student</option>
          </select>
        </div>
      </div>
    </div>

    <div class="card mb-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-3">Device settings</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label class="block text-sm text-slate-300 mb-1">ESP32-CAM address</label>
          <input v-model="form.esp32Address" placeholder="http://192.168.1.50" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200" />
          <div v-if="form.esp32Address && !validateUrl(form.esp32Address)" class="text-red-400 text-xs mt-1">Must start with http:// or https://</div>
        </div>
        <div>
          <label class="block text-sm text-slate-300 mb-1">Edge computer address</label>
          <input v-model="form.edgeComputerAddress" placeholder="http://192.168.1.10:8000" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200" />
          <div v-if="form.edgeComputerAddress && !validateUrl(form.edgeComputerAddress)" class="text-red-400 text-xs mt-1">Must start with http:// or https://</div>
        </div>
      </div>
      <p class="text-xs text-slate-500 mt-2">These are stored values for now; no connection is tested here.</p>
    </div>

    <div class="card mb-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-3">Backend API address</h2>
      <div class="text-slate-200 mb-2">http://127.0.0.1:8000/api</div>
      <div class="flex items-center gap-2">
        <button @click="testConnection" :disabled="testing" class="px-3 py-2 bg-cyan-400 text-black rounded disabled:opacity-50">{{ testing ? 'Testing...' : 'Test connection' }}</button>
        <span v-if="testResult" class="text-slate-300">{{ testResult }}</span>
      </div>
    </div>

    <div class="card mb-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-3">PDF options</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-2">
        <div>
          <label class="block text-sm text-slate-300 mb-1">Page size</label>
          <select v-model="form.pageSize" class="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded text-slate-200">
            <option>A4</option>
            <option>Letter</option>
          </select>
        </div>
        <div class="flex items-center gap-2 mt-6">
          <input type="checkbox" v-model="form.includeImages" class="accent-cyan-400 w-4 h-4" />
          <label class="text-slate-300">Include images</label>
        </div>
      </div>
      <p class="text-xs text-slate-500">These options are saved but not applied yet. The PDF generator uses its default layout.</p>
    </div>

    <div class="card mb-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-3">Email</h2>
      <button disabled class="px-3 py-2 bg-slate-800 text-slate-500 rounded">Gmail not set up yet</button>
    </div>

    <div class="flex items-center gap-2">
      <button @click="save" class="px-3 py-2 bg-cyan-400 text-black rounded">Save</button>
      <button @click="reset" class="px-3 py-2 bg-slate-700 text-slate-200 rounded">Reset to defaults</button>
      <span v-if="savedMsg" class="text-green-400">{{ savedMsg }}</span>
    </div>
  </div>
</template>