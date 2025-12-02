<template>
  <section class="log-section">
    <h2>Event Log</h2>
    <div class="log-container" ref="logContainer">
      <div 
        v-for="(log, index) in logs" 
        :key="index"
        class="log-entry"
        :class="log.type"
      >
        <span class="log-time">{{ log.time }}</span>
        <span class="log-message">{{ log.message }}</span>
      </div>
    </div>
  </section>
</template>

<script>
import { ref, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useEventLogStore } from '../../stores/eventLogStore'

export default {
  name: 'EventLogPanel',
  setup() {
    const eventLogStore = useEventLogStore()
    const { logs } = storeToRefs(eventLogStore)
    const logContainer = ref(null)

    // Auto-scroll to bottom when new logs are added
    watch(logs, () => {
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
      })
    }, { deep: true })

    return {
      logs,
      logContainer
    }
  }
}
</script>

<style scoped>
.log-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.log-section h2 {
  font-size: 0.85rem;
  color: #3498db;
  margin-bottom: 0.3rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #444;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background: #1a1a1a;
  border-radius: 4px;
  padding: 0.4rem;
  font-family: 'Courier New', monospace;
  font-size: 0.6rem;
}

.log-entry {
  padding: 0.15rem 0;
  border-bottom: 1px solid #2a2a2a;
  line-height: 1.3;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-time {
  color: #7f8c8d;
  margin-right: 0.3rem;
  font-size: 0.55rem;
}

.log-message {
  color: #bdc3c7;
}

.log-entry.system { color: #3498db; }
.log-entry.success { color: #2ecc71; }
.log-entry.error { color: #e74c3c; }
.log-entry.join { color: #f39c12; }
.log-entry.leave { color: #e67e22; }
.log-entry.action { color: #9b59b6; }
.log-entry.room { color: #ffd700; }
.log-entry.combat { color: #e74c3c; font-weight: bold; }
</style>
