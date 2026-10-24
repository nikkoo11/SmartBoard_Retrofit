<script setup>
import { ref } from 'vue'

const faqs = ref([
  { q: 'Why does Whiteboard Capture say Not connected?', a: 'ESP32-CAM hardware is not connected in this version. Use manual upload to add images.' },
  { q: 'Why is the extracted text empty?', a: 'OCR is not connected yet. You can type or edit the text manually in the capture view.' },
  { q: 'How do I create a PDF?', a: 'Go to a session with captures and use Finalize Session (or Generate PDF in PDF Archive). A PDF will be created if captures exist.' },
  { q: 'Where are my PDFs saved?', a: 'PDFs are saved on the backend under media/pdfs/ and listed in the PDF Archive.' },
  { q: 'How do I add a course?', a: 'Go to Courses > Add Course and fill in code and name.' }
])

const openFaq = ref(null)
function toggle(i) {
  openFaq.value = openFaq.value === i ? null : i
}
</script>

<template>
  <div class="p-4">
    <h1 class="text-2xl font-semibold text-cyan-400 mb-4">Help & Support</h1>

    <div class="card mb-4 p-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-3">System workflow (11 steps)</h2>
      <ol class="list-decimal list-inside space-y-2 text-slate-200">
        <li>Teacher selects a course and creates a lesson session <span class="ml-2 px-2 py-0.5 text-xs rounded bg-green-900 text-green-300">Working</span></li>
        <li>ESP32-CAM connects to Wi-Fi <span class="ml-2 px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-300">Not connected yet</span></li>
        <li>Teacher captures images with a button <span class="ml-2 px-2 py-0.5 text-xs rounded bg-yellow-900 text-yellow-300">Manual only</span></li>
        <li>Images go to the edge computer <span class="ml-2 px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-300">Not connected yet</span></li>
        <li>OpenCV preprocesses <span class="ml-2 px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-300">Not connected yet</span></li>
        <li>Tesseract extracts text <span class="ml-2 px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-300">Not connected yet</span></li>
        <li>Images and text are linked to the session <span class="ml-2 px-2 py-0.5 text-xs rounded bg-green-900 text-green-300">Working</span></li>
        <li>Finalizing compiles a PDF <span class="ml-2 px-2 py-0.5 text-xs rounded bg-green-900 text-green-300">Working</span></li>
        <li>The PDF is saved in the archive and can be emailed <span class="ml-2 px-2 py-0.5 text-xs rounded bg-green-900 text-green-300">Working</span> (Email: <span class="px-1 py-0.5 text-xs rounded bg-slate-700 text-slate-300">Not connected yet</span>)</li>
        <li>Students browse sessions and PDFs <span class="ml-2 px-2 py-0.5 text-xs rounded bg-green-900 text-green-300">Working</span></li>
        <li>The AI assistant answers using RAG <span class="ml-2 px-2 py-0.5 text-xs rounded bg-slate-700 text-slate-300">Not connected yet</span></li>
      </ol>
    </div>

    <div class="card mb-4 p-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-2">ESP32-CAM connection guide</h2>
      <p class="text-slate-400 mb-2">Planned setup. The hardware is not connected in this version.</p>
      <ol class="list-decimal list-inside space-y-1 text-slate-200">
        <li>Flash ESP32-CAM firmware with Wi-Fi credentials</li>
        <li>Connect to same network as edge computer</li>
        <li>Configure camera stream endpoint</li>
        <li>Set ESP32-CAM address in Settings (stored only)</li>
      </ol>
    </div>

    <div class="card mb-4 p-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-3">FAQ</h2>
      <div class="space-y-2">
        <div v-for="(f, i) in faqs" :key="i" class="border border-slate-700 rounded">
          <button @click="toggle(i)" class="w-full text-left px-3 py-2 bg-slate-900 text-slate-200">{{ f.q }}</button>
          <div v-if="openFaq === i" class="px-3 py-2 text-slate-300">{{ f.a }}</div>
        </div>
      </div>
    </div>

    <div class="card mb-4 p-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-3">Troubleshooting</h2>
      <ul class="space-y-2 text-slate-200">
        <li><strong>Backend not reachable:</strong> Ensure Django server is running on http://127.0.0.1:8000 and CORS allows the frontend.</li>
        <li><strong>Image upload fails:</strong> Check file type (jpg/png/webp) and that the session exists.</li>
        <li><strong>PDF cannot be created (session has no captures):</strong> Upload at least one capture before generating/finalizing.</li>
      </ul>
    </div>

    <div class="card p-4">
      <h2 class="text-lg font-semibold text-cyan-400 mb-2">About</h2>
      <p class="text-slate-200 mb-1">SmartBoard Retrofit: An IoT-Based Low-Cost Whiteboard-to-PDF Digitizer with Edge Computer Vision</p>
      <p class="text-slate-400">Tech stack: Vue 3 + Vite + Tailwind, Django REST Framework, PostgreSQL, ReportLab</p>
    </div>
  </div>
</template>