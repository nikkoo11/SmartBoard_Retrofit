<script setup>
import { ref, onMounted } from 'vue'
import { api, API_BASE } from '../services/api.js'

const STORAGE_KEY = 'smartboard_settings'
const defaults = { name: '', role: 'Teacher', esp32Address: '', edgeComputerAddress: '', pageSize: 'A4', includeImages: true }
const form       = ref({ ...defaults })
const savedMsg   = ref('')
const testing    = ref(false)
const testResult = ref('')
const testOk     = ref(null)

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    form.value = raw ? { ...defaults, ...JSON.parse(raw) } : { ...defaults }
  } catch { form.value = { ...defaults } }
}

function save() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(form.value))
    savedMsg.value = 'Settings saved.'
    setTimeout(() => { savedMsg.value = '' }, 2500)
  } catch {}
}

function reset() {
  if (!confirm('Reset all settings to defaults?')) return
  form.value = { ...defaults }
  try { localStorage.removeItem(STORAGE_KEY) } catch {}
  savedMsg.value = 'Reset to defaults.'; setTimeout(() => { savedMsg.value = '' }, 2500)
}

function validateUrl(v) { return !v || v.startsWith('http://') || v.startsWith('https://') }

async function testConnection() {
  testing.value = true; testResult.value = ''; testOk.value = null
  try {
    await api.courses()
    testOk.value    = true
    testResult.value = 'Backend connected.'
  } catch (e) {
    testOk.value = false
    testResult.value = e.status ? 'Backend returned ' + e.status : 'Cannot reach the backend.'
  }
  finally { testing.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-header">
      <h1>Settings</h1>
      <p>Preferences are saved in this browser only and do not affect the backend.</p>
    </div>

    <!-- Profile -->
    <div class="card mb-4">
      <div class="section-title">Profile</div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:.875rem;">
        <div>
          <label style="display:block; font-size:.8125rem; font-weight:500; color:var(--muted); margin-bottom:.375rem;">Name</label>
          <input v-model="form.name" placeholder="Your name" />
        </div>
        <div>
          <label style="display:block; font-size:.8125rem; font-weight:500; color:var(--muted); margin-bottom:.375rem;">Role</label>
          <select v-model="form.role">
            <option>Teacher</option>
            <option>Student</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Device settings -->
    <div class="card mb-4">
      <div class="section-title">Hardware addresses</div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:.875rem;">
        <div>
          <label style="display:block; font-size:.8125rem; font-weight:500; color:var(--muted); margin-bottom:.375rem;">ESP32-CAM address</label>
          <input v-model="form.esp32Address" placeholder="http://192.168.1.50" />
          <div v-if="form.esp32Address && !validateUrl(form.esp32Address)" style="font-size:.75rem; color:var(--danger); margin-top:.3rem;">Must start with http:// or https://</div>
        </div>
        <div>
          <label style="display:block; font-size:.8125rem; font-weight:500; color:var(--muted); margin-bottom:.375rem;">Edge computer address</label>
          <input v-model="form.edgeComputerAddress" placeholder="http://192.168.1.10:8000" />
          <div v-if="form.edgeComputerAddress && !validateUrl(form.edgeComputerAddress)" style="font-size:.75rem; color:var(--danger); margin-top:.3rem;">Must start with http:// or https://</div>
        </div>
      </div>
      <div style="font-size:.75rem; color:var(--muted); margin-top:.625rem;">These values are stored only — no live connection is made from this page.</div>
    </div>

    <!-- API connectivity -->
    <div class="card mb-4">
      <div class="section-title">Backend API</div>
      <div style="font-size:.875rem; color:var(--muted); margin-bottom:.625rem; font-family:monospace;">
        {{ API_BASE }}
      </div>
      <div style="display:flex; align-items:center; gap:.625rem; flex-wrap:wrap;">
        <button class="btn btn-secondary btn-sm" @click="testConnection" :disabled="testing">
          <span v-if="testing" class="spinner" style="width:12px;height:12px;border-width:2px;"></span>
          {{ testing ? 'Testing…' : 'Test connection' }}
        </button>
        <span v-if="testResult" :style="testOk ? 'color:var(--success);' : 'color:var(--danger);'" style="font-size:.875rem;">
          {{ testResult }}
        </span>
      </div>
    </div>

    <!-- PDF options -->
    <div class="card mb-4">
      <div class="section-title">PDF options</div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:.875rem; margin-bottom:.625rem;">
        <div>
          <label style="display:block; font-size:.8125rem; font-weight:500; color:var(--muted); margin-bottom:.375rem;">Page size</label>
          <select v-model="form.pageSize" style="width:auto; min-width:100px;">
            <option>A4</option>
            <option>Letter</option>
          </select>
        </div>
        <div style="display:flex; align-items:center; gap:.5rem; padding-top:1.5rem;">
          <input type="checkbox" id="inc-images" v-model="form.includeImages" style="width:15px;height:15px; accent-color:var(--accent); cursor:pointer;" />
          <label for="inc-images" style="font-size:.875rem; color:var(--text); cursor:pointer;">Include board images</label>
        </div>
      </div>
      <div style="font-size:.75rem; color:var(--muted);">These preferences are stored but not yet applied to the PDF generator.</div>
    </div>

    <!-- Save / Reset -->
    <div style="display:flex; align-items:center; gap:.625rem; flex-wrap:wrap;">
      <button class="btn btn-primary" @click="save">Save settings</button>
      <button class="btn btn-secondary" @click="reset">Reset to defaults</button>
      <span v-if="savedMsg" style="font-size:.875rem; color:var(--success);">{{ savedMsg }}</span>
    </div>
  </div>
</template>
