<template>
  <div>
    <h1>AI Assistant</h1>
    <div class="card">
      <div v-for="(m,i) in messages" :key="i" style="margin:.5rem 0;"><b>{{ m.role }}:</b> {{ m.text }}</div>
      <input v-model="input" placeholder="Ask about a lesson" />
      <button @click="send">Send</button>
      <p v-if="loading">Generating...</p>
      <p v-if="error">{{ error }}</p>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
const messages = ref([]); const input = ref(''); const loading = ref(false); const error = ref('')
function send(){ if(!input.value.trim()) return; messages.value.push({role:'user',text:input.value}); input.value=''; error.value='AI service not connected (demo).'; }
</script>
