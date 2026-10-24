<template>
  <div>
    <h1>Courses</h1>
    <div class="card">
      <input v-model="search" placeholder="Search courses" />
      <p v-if="!courses.length">No courses (demo).</p>
      <ul><li v-for="c in filtered" :key="c.id">{{ c.code }} - {{ c.title }}</li></ul>
    </div>
  </div>
</template>
<script setup>
import { ref, computed } from 'vue'
const search = ref('')
const courses = ref([])
const filtered = computed(() => courses.value.filter(c => (c.title||'').toLowerCase().includes(search.value.toLowerCase())))
</script>
