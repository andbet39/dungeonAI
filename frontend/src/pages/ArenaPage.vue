<template>
  <div class="arena-page">
    <header class="arena-header">
      <router-link to="/" class="back-btn">← Home</router-link>
      <h1>AI Test Arena</h1>
    </header>
    <div class="arena-content">
      <AITestArena v-if="loaded" />
      <div v-else class="loading">Loading...</div>
    </div>
  </div>
</template>

<script>
import { defineAsyncComponent } from 'vue'

export default {
  name: 'ArenaPage',
  components: {
    AITestArena: defineAsyncComponent(() => import('../components/AITestArena.vue'))
  },
  data() {
    return {
      loaded: false
    }
  },
  mounted() {
    this.loaded = true
  }
}
</script>

<style scoped>
.arena-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--p-surface-ground);
  color: var(--p-text-color);
}

.arena-header {
  padding: 0.75rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  background: var(--p-surface-card);
  border-bottom: 1px solid var(--p-surface-border);
}

.arena-header h1 {
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0;
  color: var(--p-text-color);
}

.back-btn {
  color: var(--p-primary-color);
  text-decoration: none;
  font-size: 0.9rem;
}

.back-btn:hover {
  text-decoration: underline;
}

.arena-content {
  flex: 1;
  overflow-y: auto;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: var(--p-text-muted-color);
}
</style>
