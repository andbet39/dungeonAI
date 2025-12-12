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
  font-size: 0.9rem;
  color: #ffd700;
  margin-bottom: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
  font-weight: 700;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  padding: 0.6rem;
  font-family: 'Courier New', monospace;
  font-size: 0.65rem;
  border: 1px solid rgba(255, 215, 0, 0.15);
}

.log-container::-webkit-scrollbar {
  width: 8px;
}

.log-container::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb {
  background: rgba(255, 215, 0, 0.3);
  border-radius: 4px;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 215, 0, 0.5);
}

.log-entry {
  padding: 0.25rem 0;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
  line-height: 1.4;
  transition: all 0.2s ease;
}

.log-entry:hover {
  background: rgba(255, 215, 0, 0.05);
  padding-left: 0.3rem;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-time {
  color: #8e949e;
  margin-right: 0.4rem;
  font-size: 0.6rem;
  font-weight: 600;
}

.log-message {
  color: #c5d0dc;
}

.log-entry.system { color: #5dade2; }
.log-entry.system .log-message { color: #5dade2; }

.log-entry.success { color: #27ae60; }
.log-entry.success .log-message { color: #27ae60; }

.log-entry.error { color: #e74c3c; }
.log-entry.error .log-message { color: #e74c3c; }

.log-entry.join { color: #f39c12; }
.log-entry.join .log-message { color: #f39c12; }

.log-entry.leave { color: #e67e22; }
.log-entry.leave .log-message { color: #e67e22; }

.log-entry.action { color: #9b59b6; }
.log-entry.action .log-message { color: #9b59b6; }

.log-entry.room { color: #ffd700; }
.log-entry.room .log-message { color: #ffd700; text-shadow: 0 0 5px rgba(255, 215, 0, 0.3); }

.log-entry.combat { color: #e74c3c; font-weight: 700; }
.log-entry.combat .log-message { color: #e74c3c; font-weight: 700; }
</style>
