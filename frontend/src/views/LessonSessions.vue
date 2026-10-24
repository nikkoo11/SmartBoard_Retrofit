<template>
  <div>
    <h1>Lesson Sessions</h1>
    <div class="card">
      <p v-if="!records.length">No sessions. Create one after backend support.</p>
      <table v-else><thead><tr><th>ID</th><th>Status</th><th>Created</th></tr></thead><tbody><tr v-for="r in records" :key="r.id"><td>{{r.id}}</td><td>{{r.status}}</td><td>{{r.created_at}}</td></tr></tbody></table>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../services/api.js'
const records = ref([])
onMounted(async () => { try { const d = await api.records(); records.value = d.results || [] } catch(e){} })
</script>
