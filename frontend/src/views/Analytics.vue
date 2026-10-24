<template>
  <div>
    <h1>Analytics</h1>
    <div class="card">Total records: {{ data?.total ?? 0 }} (demo)</div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../services/api.js'
const data = ref(null)
onMounted(async () => { try { data.value = await api.analytics() } catch(e){} })
</script>
