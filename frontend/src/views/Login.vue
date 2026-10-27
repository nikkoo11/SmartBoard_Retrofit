<template>
  <div class="min-h-screen flex items-center justify-center px-4">
    <div class="card w-full max-w-sm">
      <div class="mb-6 text-center">
        <h1 class="text-xl font-semibold">Teacher Login</h1>
        <p class="text-sm text-gray-500 mt-1">Sign in to manage SmartBoard sessions.</p>
      </div>

      <form @submit.prevent="submit" class="space-y-4" novalidate>
        <div>
          <label for="username" class="block text-sm font-medium mb-1">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            name="username"
            autocomplete="username"
            required
            class="w-full border rounded px-3 py-2"
            :disabled="loading"
          />
        </div>

        <div>
          <label for="password" class="block text-sm font-medium mb-1">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            name="password"
            autocomplete="current-password"
            required
            class="w-full border rounded px-3 py-2"
            :disabled="loading"
          />
        </div>

        <p v-if="error" class="text-sm text-red-600" role="alert">{{ error }}</p>

        <button
          type="submit"
          class="w-full rounded px-3 py-2 bg-blue-600 text-white disabled:opacity-50"
          :disabled="loading || !username || !password"
        >
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '../composables/useAuth.js'

const router = useRouter()
const route = useRoute()
const { login, loading, error } = useAuth()

const username = ref('')
const password = ref('')

function safeRedirect(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') && value !== '/login'
    ? value
    : '/dashboard'
}

async function submit() {
  if (loading.value) return
  try {
    await login(username.value, password.value)
    password.value = ''
    await router.push(safeRedirect(route.query.redirect))
  } catch (e) {
    // error is already surfaced by useAuth
  }
}
</script>
