<script setup>
import { ref } from 'vue'

const faqs = ref([
  { q: 'Why does Whiteboard Capture say "Not connected"?', a: 'ESP32-CAM hardware is not connected in this version. Use the manual image upload to add board captures.' },
  { q: 'Why is the extracted text empty?', a: 'Select a capture in the Whiteboard Capture view, choose an OCR engine (Tesseract or Gemini), and click Run OCR. You can also type or edit text manually.' },
  { q: 'How do I create a PDF?', a: 'Go to the Whiteboard Capture view, select a session, upload captures, run OCR on them, save the text, then click Finalize Session. Alternatively use Generate PDF from the PDF Archive page.' },
  { q: 'Where are PDFs saved?', a: 'PDFs are saved on the backend under media/pdfs/ and are listed in the PDF Archive.' },
  { q: 'How do I add a course?', a: 'Go to Courses → Add Course and fill in the course code and name.' }
])

const openFaq = ref(null)
function toggle(i) { openFaq.value = openFaq.value === i ? null : i }
</script>

<template>
  <div>
    <div class="page-header">
      <h1>Help &amp; Support</h1>
      <p>System documentation, workflow guide, and frequently asked questions.</p>
    </div>

    <!-- Workflow status -->
    <div class="card mb-4">
      <div class="section-title">System workflow</div>
      <ol style="margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:.625rem;">
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">1</span>
          <span>Teacher selects a course and creates a lesson session</span>
          <span class="badge badge-finalized" style="margin-left:auto; flex-shrink:0;">Working</span>
        </li>
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">2</span>
          <span>ESP32-CAM connects to Wi-Fi and streams images</span>
          <span class="badge badge-draft" style="margin-left:auto; flex-shrink:0;">Not connected</span>
        </li>
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">3</span>
          <span>Board images are captured (manual upload available)</span>
          <span class="badge badge-capturing" style="margin-left:auto; flex-shrink:0;">Manual only</span>
        </li>
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">4</span>
          <span>OpenCV cleans and preprocesses images</span>
          <span class="badge badge-finalized" style="margin-left:auto; flex-shrink:0;">Working</span>
        </li>
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">5</span>
          <span>Tesseract / Gemini extracts text via OCR</span>
          <span class="badge badge-finalized" style="margin-left:auto; flex-shrink:0;">Working</span>
        </li>
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">6</span>
          <span>Images and text are linked to the lesson session</span>
          <span class="badge badge-finalized" style="margin-left:auto; flex-shrink:0;">Working</span>
        </li>
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">7</span>
          <span>Session is finalized and compiled into a PDF</span>
          <span class="badge badge-finalized" style="margin-left:auto; flex-shrink:0;">Working</span>
        </li>
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">8</span>
          <span>PDF saved in archive; students can browse sessions</span>
          <span class="badge badge-finalized" style="margin-left:auto; flex-shrink:0;">Working</span>
        </li>
        <li style="display:flex; align-items:baseline; gap:.75rem; font-size:.875rem;">
          <span style="flex-shrink:0; width:1.25rem; color:var(--muted); text-align:right; font-size:.75rem; font-weight:600;">9</span>
          <span>AI Assistant answers using RAG on lesson notes</span>
          <span class="badge badge-draft" style="margin-left:auto; flex-shrink:0;">Planned</span>
        </li>
      </ol>
    </div>

    <!-- FAQ -->
    <div class="card mb-4">
      <div class="section-title">Frequently asked questions</div>
      <div style="display:flex; flex-direction:column; gap:.375rem;">
        <div v-for="(f, i) in faqs" :key="i" style="border:1px solid var(--border); border-radius:.5rem; overflow:hidden;">
          <button
            @click="toggle(i)"
            style="width:100%; text-align:left; padding:.75rem 1rem; background:var(--panel2); color:var(--text); font-size:.875rem; font-weight:500; display:flex; align-items:center; justify-content:space-between; gap:.5rem; border:none;"
          >
            {{ f.q }}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0;transition:transform .2s;" :style="openFaq===i?'transform:rotate(180deg);':''"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
          <div v-if="openFaq === i" style="padding:.75rem 1rem; font-size:.875rem; color:var(--muted); border-top:1px solid var(--border);">{{ f.a }}</div>
        </div>
      </div>
    </div>

    <!-- Troubleshooting -->
    <div class="card mb-4">
      <div class="section-title">Troubleshooting</div>
      <ul style="margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:.625rem;">
        <li style="font-size:.875rem;"><strong style="color:var(--text);">Backend not reachable:</strong> <span style="color:var(--muted);">Ensure the Django server is running on <code style="background:var(--bg);padding:.1rem .4rem;border-radius:.25rem;">http://127.0.0.1:8000</code> and CORS allows the frontend origin.</span></li>
        <li style="font-size:.875rem;"><strong style="color:var(--text);">Image upload fails:</strong> <span style="color:var(--muted);">Check the file type (jpg/png/webp), file size, and that a session is selected.</span></li>
        <li style="font-size:.875rem;"><strong style="color:var(--text);">PDF cannot be generated:</strong> <span style="color:var(--muted);">Upload at least one capture and save extracted text before generating or finalizing.</span></li>
        <li style="font-size:.875rem;"><strong style="color:var(--text);">Gemini OCR fails:</strong> <span style="color:var(--muted);">Check that <code style="background:var(--bg);padding:.1rem .4rem;border-radius:.25rem;">GEMINI_API_KEY</code> is set in the backend <code style="background:var(--bg);padding:.1rem .4rem;border-radius:.25rem;">.env</code> file and verify the model name.</span></li>
      </ul>
    </div>

    <!-- About -->
    <div class="card">
      <div class="section-title">About</div>
      <div style="font-size:.9375rem; font-weight:500; color:var(--text); margin-bottom:.375rem;">SmartBoard Retrofit</div>
      <div style="font-size:.875rem; color:var(--muted); margin-bottom:.5rem;">An IoT-based low-cost whiteboard-to-PDF digitizer with edge computer vision and AI-assisted OCR.</div>
      <div style="font-size:.8125rem; color:var(--muted);">Stack: Vue 3 · Vite · Tailwind CSS · Django REST Framework · PostgreSQL · ReportLab · Tesseract · Gemini API</div>
    </div>
  </div>
</template>
