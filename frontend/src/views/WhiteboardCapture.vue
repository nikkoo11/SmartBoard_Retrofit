<template>
  <div>
    <h1>Whiteboard Capture</h1>
    <div class="card">ESP32-CAM: disconnected (demo). No capture available until hardware connected.</div>
    <div class="card">
      <input type="file" accept="image/*" @change="onFile" />
      <img v-if="preview" :src="preview" style="max-width:300px;" />
      <button @click="upload" :disabled="!file">Upload test image</button>
      <p>{{ result }}</p>
    </div>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { api } from '../services/api.js'
const file = ref(null); const preview = ref(''); const result = ref('')
function onFile(e){ file.value=e.target.files[0]; preview.value=URL.createObjectURL(file.value) }
async function upload(){ const fd=new FormData(); fd.append('image',file.value); try{const r=await api.uploadImage(fd); result.value=JSON.stringify(r)}catch(e){result.value='Upload failed'} }
</script>
