<template>
  <div>
    <div class="page-header">
      <h1>AI Assistant</h1>
      <p>Ask questions about your lesson sessions and captured content.</p>
    </div>

    <div class="card" style="max-width:640px;">
      <!-- Coming soon notice -->
      <div style="display:flex; flex-direction:column; align-items:center; gap:.875rem; padding:2rem 1rem; text-align:center; border-bottom:1px solid var(--border); margin-bottom:1.25rem;">
        <div style="width:52px; height:52px; border-radius:.75rem; background:color-mix(in srgb,var(--accent) 15%,transparent); display:flex; align-items:center; justify-content:center;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" style="width:26px;height:26px;color:var(--accent);"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        </div>
        <div>
          <div style="font-size:1rem; font-weight:600; color:var(--text); margin-bottom:.3rem;">AI Assistant — Coming Soon</div>
          <div style="font-size:.875rem; color:var(--muted); max-width:380px;">This feature will use RAG (Retrieval-Augmented Generation) to answer questions about your lesson notes. It is planned for a future version.</div>
        </div>
      </div>

      <!-- Demo chat area (non-functional) -->
      <div style="min-height:160px; background:var(--bg); border:1px solid var(--border); border-radius:.5rem; padding:1rem; margin-bottom:.875rem; display:flex; flex-direction:column; gap:.625rem; overflow-y:auto;">
        <div v-for="(m, i) in messages" :key="i" :style="m.role === 'user' ? 'align-self:flex-end; background:color-mix(in srgb,var(--accent) 20%,transparent); color:var(--text); padding:.5rem .875rem; border-radius:.75rem .75rem 0 .75rem; max-width:80%; font-size:.875rem;' : 'align-self:flex-start; background:var(--panel2); color:var(--muted); padding:.5rem .875rem; border-radius:.75rem .75rem .75rem 0; max-width:80%; font-size:.875rem;'">
          {{ m.text }}
        </div>
        <div v-if="messages.length === 0" style="margin:auto; color:var(--muted); font-size:.875rem; text-align:center;">No messages yet. Try asking a question below.</div>
      </div>

      <div style="display:flex; gap:.5rem;">
        <input v-model="input" placeholder="Ask about a lesson (demo only)…" @keydown.enter="send" style="flex:1;" />
        <button class="btn btn-primary btn-sm" @click="send" style="flex-shrink:0;">Send</button>
      </div>
      <div v-if="error" class="alert alert-warn" style="margin-top:.625rem; margin-bottom:0;">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const messages = ref([])
const input    = ref('')
const error    = ref('')

function send() {
  if (!input.value.trim()) return
  messages.value.push({ role: 'user', text: input.value })
  input.value = ''
  setTimeout(() => {
    messages.value.push({ role: 'assistant', text: 'AI service is not connected yet. This feature is planned for a future version.' })
    error.value = ''
  }, 400)
}
</script>
