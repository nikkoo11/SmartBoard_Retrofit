<template>
  <div class="layout">
    <nav class="sidebar">
      <h2>SmartBoard</h2>
      <router-link to="/dashboard">Dashboard</router-link>
      <router-link to="/courses">Courses</router-link>
      <router-link to="/sessions">Lesson Sessions</router-link>
      <router-link to="/capture">Whiteboard Capture</router-link>
      <router-link to="/archive">PDF Archive</router-link>
      <router-link to="/assistant">AI Assistant</router-link>
      <router-link to="/settings">Settings</router-link>
      <router-link to="/help">Help & Support</router-link>
    </nav>
    <main class="main"><router-view/></main>
  </div>
</template>
