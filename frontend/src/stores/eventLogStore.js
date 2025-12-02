import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useEventLogStore = defineStore('eventLog', () => {
  const logs = ref([])
  const maxLogs = 100

  /**
   * Add a log entry with timestamp
   * @param {string} message - The log message
   * @param {string} type - Log type: 'info', 'system', 'success', 'error', 'join', 'leave', 'action', 'room', 'combat'
   */
  function addLog(message, type = 'info') {
    const now = new Date()
    const time = now.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })

    logs.value.push({ time, message, type })

    // Keep log size bounded
    if (logs.value.length > maxLogs) {
      logs.value.shift()
    }
  }

  /**
   * Clear all logs
   */
  function clearLogs() {
    logs.value = []
  }

  return {
    logs,
    addLog,
    clearLogs
  }
})
