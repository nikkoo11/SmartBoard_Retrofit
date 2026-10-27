import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import { useAuth } from './composables/useAuth.js'

const app = createApp(App).use(router).mount('#app')

// Restore teacher session state from the existing Django session once at startup.
// Hydration is non-blocking and failures are handled inside useAuth.
useAuth().hydrate().catch(() => {})
