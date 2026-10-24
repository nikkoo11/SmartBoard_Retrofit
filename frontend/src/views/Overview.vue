<template>
  <div>
    <h1>Dashboard</h1>
    <p class="muted">Manage lessons and digitized whiteboard notes.</p>
    <div class="grid">
      <div class="card">ESP32-CAM: disconnected (demo)</div>
      <div class="card">Wi-Fi: unknown (demo)</div>
      <div class="card">Backend: {{ summary.system_status || 'Demo Mode' }}</div>
      <div class="card">Edge computer: local</div>
    </div>
    <div class="grid">
      <div class="card">Total courses: 0 (demo)</div>
      <div class="card">Total sessions: {{ summary.total_records || 0 }}</div>
      <div class="card">Archived PDFs: 0 (demo)</div>
    </div>
    <div class="card">
      <button @click="$router.push('/sessions')">Create Session</button>
      <button @click="$router.push('/capture')">Capture Whiteboard</button>
      <button @click="$router.push('/archive')">Browse PDF Archive</button>
      <button @click="$router.push('/assistant')">Ask AI</button>
    </div>
    <div class="card"><h3>Recent sessions</h3><p v-if="!records.length">No sessions.</p><ul><li v-for="r in records" :key="r.id">{{ r.id }} - {{ r.status }}</li></ul></div>
    <div class="card"><h3>Recent activity</h3><p>Demo: no activity yet.</p></div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../services/api.js'
const summary = ref({}); const records = ref([])
onMounted(async () => { try { summary.value = await api.dashboardSummary(); const d = await api.records(); records.value = d.results || [] } catch(e){} })
</script>
<style scoped>.muted{color:var(--muted);}</style>
