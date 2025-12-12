<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h2>🏆 Global Leaderboard</h2>
            <button class="close-btn" @click="close">✕</button>
          </div>

          <div class="modal-body">
            <!-- Loading State -->
            <div v-if="loading" class="loading-state">
              <div class="loading-spinner"></div>
              <p>Loading rankings...</p>
            </div>

            <!-- Leaderboard Content -->
            <div v-else-if="leaderboard.length > 0" class="leaderboard-content">
              <div class="leaderboard-stats">
                <span>Total Heroes: {{ totalPlayers }}</span>
                <button class="refresh-btn" @click="refresh" :disabled="loading">
                  <span v-if="!loading">🔄 Refresh</span>
                  <span v-else>...</span>
                </button>
              </div>

              <div class="leaderboard-list">
                <div
                  v-for="entry in leaderboard"
                  :key="entry.token"
                  class="leaderboard-entry"
                  :class="{ 
                    'my-entry': entry.token === playerToken,
                    'top-three': entry.rank <= 3
                  }"
                >
                  <!-- Rank Badge -->
                  <div class="rank-badge" :class="`rank-${entry.rank}`">
                    <span v-if="entry.rank === 1" class="trophy">🥇</span>
                    <span v-else-if="entry.rank === 2" class="trophy">🥈</span>
                    <span v-else-if="entry.rank === 3" class="trophy">🥉</span>
                    <span v-else class="rank-number">#{{ entry.rank }}</span>
                  </div>

                  <!-- Player Info -->
                  <div class="player-details">
                    <div class="player-name-section">
                      <h3 class="player-name">{{ entry.full_title }}</h3>
                      <span v-if="entry.token === playerToken" class="you-badge">YOU</span>
                    </div>

                    <!-- Stats Grid -->
                    <div class="stats-row">
                      <div class="stat-item primary">
                        <span class="stat-icon">⭐</span>
                        <span class="stat-value">{{ entry.experience }}</span>
                        <span class="stat-label">XP</span>
                      </div>
                      <div class="stat-item">
                        <span class="stat-icon">⚔️</span>
                        <span class="stat-value">{{ entry.kills }}</span>
                        <span class="stat-label">Kills</span>
                      </div>
                      <div class="stat-item" v-if="entry.top_kill">
                        <span class="stat-icon">💀</span>
                        <span class="stat-value">{{ formatMonsterType(entry.top_kill) }}</span>
                        <span class="stat-label">Top Kill</span>
                      </div>
                    </div>
                  </div>

                  <!-- Rank Position Indicator -->
                  <div class="position-indicator">
                    <span class="position-text">{{ getPositionText(entry.rank) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Empty State -->
            <div v-else class="empty-state">
              <p class="empty-icon">🏜️</p>
              <p class="empty-text">No heroes on the leaderboard yet</p>
              <p class="empty-hint">Be the first to slay monsters and claim glory!</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  playerToken: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close'])

const leaderboard = ref([])
const totalPlayers = ref(0)
const loading = ref(false)

// Fetch leaderboard data
const fetchLeaderboard = async () => {
  console.log('fetchLeaderboard called, setting loading to true')
  loading.value = true
  try {
    console.log('Fetching leaderboard from API...')
    const response = await fetch('/api/leaderboard?limit=50', {
      credentials: 'include'
    })
    console.log('Leaderboard response status:', response.status, 'ok:', response.ok)
    
    if (response.ok) {
      const data = await response.json()
      console.log('Leaderboard data received:', data)
      console.log('Leaderboard array:', data.leaderboard)
      console.log('Is array?', Array.isArray(data.leaderboard))
      
      leaderboard.value = data.leaderboard || []
      totalPlayers.value = data.total_players || 0
      
      console.log('Leaderboard ref updated, length:', leaderboard.value.length)
      console.log('Total players:', totalPlayers.value)
    } else {
      console.error('Response not ok:', response.status, response.statusText)
      const errorText = await response.text()
      console.error('Error response:', errorText)
    }
  } catch (e) {
    console.error('Error fetching leaderboard:', e)
    console.error('Error stack:', e.stack)
  } finally {
    console.log('Finally block, setting loading to false')
    loading.value = false
    console.log('Loading is now:', loading.value)
  }
}

// Refresh leaderboard
const refresh = () => {
  fetchLeaderboard()
}

// Close modal
const close = () => {
  emit('close')
}

// Watch for modal open to fetch data
watch(() => props.isOpen, (isOpen) => {
  console.log('Modal isOpen changed:', isOpen)
  if (isOpen) {
    console.log('Modal opened, fetching leaderboard...')
    fetchLeaderboard()
  }
}, { immediate: true })

// Format monster type
const formatMonsterType = (topKill) => {
  if (!topKill) return 'None'
  // Handle array format: ["monster_type", count]
  const monsterType = Array.isArray(topKill) ? topKill[0] : topKill
  if (!monsterType) return 'None'
  return monsterType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// Get position text
const getPositionText = (rank) => {
  if (rank === 1) return 'Champion'
  if (rank === 2) return 'Elite'
  if (rank === 3) return 'Master'
  if (rank <= 10) return 'Expert'
  if (rank <= 25) return 'Veteran'
  return 'Hero'
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-container {
  background: rgba(20, 25, 40, 0.98);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 20px;
  width: 100%;
  max-width: 800px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6), 0 0 100px rgba(255, 215, 0, 0.15);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.75rem 2rem;
  border-bottom: 1px solid rgba(255, 215, 0, 0.2);
  background: linear-gradient(135deg, rgba(241, 196, 15, 0.12) 0%, rgba(243, 156, 18, 0.06) 100%);
}

.modal-header h2 {
  font-size: 1.75rem;
  color: #ffd700;
  margin: 0;
  font-weight: 700;
  letter-spacing: -0.01em;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
}

.close-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ecf0f1;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.5rem;
  transition: all 0.3s ease;
  line-height: 1;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 215, 0, 0.5);
  transform: rotate(90deg);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.modal-body::-webkit-scrollbar {
  width: 8px;
}

.modal-body::-webkit-scrollbar-track {
  background: rgba(255, 215, 0, 0.05);
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-thumb {
  background: rgba(255, 215, 0, 0.3);
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 215, 0, 0.5);
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid rgba(255, 215, 0, 0.1);
  border-top: 4px solid #ffd700;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1.5rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-state p {
  color: #a0aec0;
  font-size: 1.1rem;
}

/* Leaderboard Stats Header */
.leaderboard-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding: 1rem 1.5rem;
  background: rgba(15, 18, 30, 0.7);
  border-radius: 12px;
  border: 1px solid rgba(255, 215, 0, 0.2);
}

.leaderboard-stats span {
  color: #ffd700;
  font-weight: 600;
  font-size: 1rem;
}

.refresh-btn {
  background: rgba(52, 152, 219, 0.15);
  color: #5dade2;
  border: 1px solid rgba(52, 152, 219, 0.4);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(52, 152, 219, 0.25);
  border-color: rgba(52, 152, 219, 0.6);
  transform: translateY(-1px);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Leaderboard List */
.leaderboard-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.leaderboard-entry {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 1.5rem;
  align-items: center;
  background: rgba(15, 18, 30, 0.7);
  backdrop-filter: blur(10px);
  padding: 1.5rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 215, 0, 0.2);
  transition: all 0.3s ease;
}

.leaderboard-entry:hover {
  background: rgba(15, 18, 30, 0.9);
  border-color: rgba(255, 215, 0, 0.35);
  transform: translateX(4px);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4);
}

.leaderboard-entry.my-entry {
  background: rgba(52, 152, 219, 0.2);
  border-color: rgba(52, 152, 219, 0.5);
  box-shadow: 0 0 30px rgba(52, 152, 219, 0.2);
}

.leaderboard-entry.my-entry:hover {
  border-color: rgba(52, 152, 219, 0.7);
  box-shadow: 0 6px 30px rgba(52, 152, 219, 0.3);
}

.leaderboard-entry.top-three {
  background: linear-gradient(135deg, rgba(241, 196, 15, 0.12) 0%, rgba(15, 18, 30, 0.9) 100%);
}

/* Rank Badge */
.rank-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 12px;
  background: rgba(255, 215, 0, 0.1);
  border: 2px solid rgba(255, 215, 0, 0.3);
  transition: all 0.3s ease;
}

.rank-badge.rank-1,
.rank-badge.rank-2,
.rank-badge.rank-3 {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.2) 0%, rgba(255, 215, 0, 0.1) 100%);
  border-color: rgba(255, 215, 0, 0.5);
}

.trophy {
  font-size: 2rem;
  line-height: 1;
}

.rank-number {
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffd700;
}

/* Player Details */
.player-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-width: 0;
}

.player-name-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.player-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #ffd700;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.you-badge {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

/* Stats Row */
.stats-row {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.875rem;
  background: rgba(255, 215, 0, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 215, 0, 0.15);
}

.stat-item.primary {
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.2) 0%, rgba(142, 68, 173, 0.1) 100%);
  border-color: rgba(155, 89, 182, 0.4);
}

.stat-icon {
  font-size: 1rem;
}

.stat-value {
  font-size: 1rem;
  font-weight: 700;
  color: #ffd700;
}

.stat-item.primary .stat-value {
  color: #e8a2ff;
}

.stat-label {
  font-size: 0.75rem;
  color: #a0aec0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Position Indicator */
.position-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
}

.position-text {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.2) 0%, rgba(255, 215, 0, 0.1) 100%);
  color: #ffd700;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
  border: 1px solid rgba(255, 215, 0, 0.3);
  white-space: nowrap;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-text {
  font-size: 1.25rem;
  color: #ecf0f1;
  margin-bottom: 0.5rem;
  font-weight: 600;
}

.empty-hint {
  font-size: 1rem;
  color: #a0aec0;
}

/* Modal Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.9);
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .modal-container {
    max-width: 100%;
    border-radius: 16px;
  }

  .modal-header {
    padding: 1.25rem 1.5rem;
  }

  .modal-header h2 {
    font-size: 1.4rem;
  }

  .modal-body {
    padding: 1.25rem;
  }

  .leaderboard-entry {
    grid-template-columns: auto 1fr;
    gap: 1rem;
    padding: 1rem;
  }

  .position-indicator {
    grid-column: 1 / -1;
    justify-content: flex-start;
    margin-top: 0.5rem;
  }

  .rank-badge {
    width: 50px;
    height: 50px;
  }

  .trophy {
    font-size: 1.5rem;
  }

  .rank-number {
    font-size: 1.25rem;
  }

  .stats-row {
    gap: 0.75rem;
  }

  .stat-item {
    padding: 0.375rem 0.625rem;
  }

  .player-name {
    font-size: 1.1rem;
  }
}
</style>
