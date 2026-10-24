<template>
  <div>
    <h1>Settings</h1>
    <div class="card">API base: {{ apiBase }}</div>
    <div class="card">Camera: disconnected (demo)</div>
  </div>
</template>
<script setup>
const apiBase = import.meta.env.VITE_API_BASE_URL
</script>
