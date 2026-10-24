<template>
  <div class="layout">
    <button class="menu-toggle" @click="open = !open" aria-label="Toggle navigation">☰</button>
    <nav class="sidebar" :class="{ open }">
      <h2>SmartBoard</h2>
      <router-link to="/dashboard" @click="open = false">Dashboard</router-link>
      <router-link to="/courses" @click="open = false">Courses</router-link>
      <router-link to="/sessions" @click="open = false">Lesson Sessions</router-link>
      <router-link to="/capture" @click="open = false">Whiteboard Capture</router-link>
      <router-link to="/archive" @click="open = false">PDF Archive</router-link>
      <router-link to="/assistant" @click="open = false">AI Assistant</router-link>
      <router-link to="/settings" @click="open = false">Settings</router-link>
      <router-link to="/help" @click="open = false">Help & Support</router-link>
    </nav>
    <main class="main mx-auto w-full max-w-[1400px]"><router-view/></main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const open = ref(false)
</script>

<style>
.sidebar a:hover {
  background: #1e293b;
  color: var(--accent);
}
.sidebar a.router-link-active {
  background: rgba(34, 211, 238, 0.15);
  color: var(--accent);
  font-weight: 600;
}
</style>
