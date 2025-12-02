<template>
  <div class="lobby-page">
    <header class="header">
      <div class="header-left">
        <router-link to="/" class="back-btn">← Home</router-link>
        <h1>🗡️ DungeonAI Lobby</h1>
      </div>
      <div class="header-right">
        <div class="player-info" v-if="playerToken">
          <div class="name-edit-container">
            <input 
              v-if="isEditingName"
              ref="nameInput"
              type="text"
              v-model="editingName"
              class="name-input"
              @blur="saveName"
              @keyup.enter="saveName"
              @keyup.escape="cancelEditName"
              maxlength="30"
              placeholder="Enter your name"
            />
            <span v-else class="player-name" @click="startEditName">
              🎮 {{ fullTitle }}
              <span class="edit-hint">✏️</span>
            </span>
          </div>
          <div class="player-xp" v-if="playerStats">
            ⭐ {{ playerStats.experience_earned || 0 }} XP
          </div>
        </div>
      </div>
    </header>

    <main class="lobby-content">
      <!-- Loading State -->
      <div class="loading-state" v-if="isLoading">
        <div class="loading-spinner"></div>
        <p>Loading games...</p>
      </div>

      <!-- Error State -->
      <div class="error-state" v-else-if="error">
        <p class="error-message">{{ error }}</p>
        <button class="retry-btn" @click="fetchGames">Retry</button>
      </div>

      <!-- Main Lobby Content - Two Column Layout -->
      <div class="two-column-layout" v-else>
        <!-- Left Column: Game Related Content -->
        <div class="left-column">
          <!-- Quick Join Section -->
          <section class="quick-join-section">
            <h2>⚔️ Quick Join</h2>
            <p class="section-desc">Jump into the action immediately</p>
            <button class="quick-join-btn" @click="quickJoin" :disabled="isJoining">
              <span v-if="isJoining">Joining...</span>
              <span v-else>🎲 Find a Game</span>
            </button>
          </section>

          <!-- Create Game Section -->
          <section class="create-section">
            <h2>🏰 Create New Game</h2>
            <p class="section-desc">Start a new dungeon adventure</p>
            <div class="create-form">
              <input 
                type="text" 
                v-model="customGameName" 
                placeholder="Custom name (optional - AI will generate one)"
                class="game-name-input"
              />
              <div class="map-size-options">
                <label class="size-label">Map Size:</label>
                <select v-model="selectedMapSize" class="size-select">
                  <option value="small">🗺️ Small (60×40, 6 rooms)</option>
                  <option value="medium">🗺️ Medium (100×60, 10 rooms)</option>
                  <option value="large">🗺️ Large (150×80, 15 rooms)</option>
                  <option value="huge">🗺️ Huge (200×100, 20 rooms)</option>
                </select>
              </div>
              <button class="create-btn" @click="createGame" :disabled="isCreating">
                <span v-if="isCreating">Creating...</span>
                <span v-else>✨ Create Game</span>
              </button>
            </div>
          </section>

          <!-- Available Games Section -->
          <section class="games-section">
            <div class="games-header">
              <h2>🎮 Available Games</h2>
              <button class="refresh-btn" @click="fetchGames" :disabled="isLoading">
                🔄 Refresh
              </button>
            </div>

            <div class="games-list" v-if="games.length > 0">
              <div 
                v-for="game in games" 
                :key="game.game_id" 
                class="game-card"
                :class="{ 'joinable': game.is_joinable, 'completed': game.is_completed && !game.is_joinable, 'full': !game.is_joinable && !game.is_completed }"
              >
                <div class="game-info">
                  <h3 class="game-name">{{ game.name }}</h3>
                  <div class="game-meta">
                    <span class="player-count">
                      👥 {{ game.player_count }} / {{ game.max_players }}
                    </span>
                    <span class="game-status" :class="{ 'completed': game.is_completed }">
                      {{ game.is_completed ? '✅ Completed' : '🎮 Active' }}
                    </span>
                  </div>
                  <div class="game-id">ID: {{ game.game_id }}</div>
                </div>
                <div class="game-actions">
                  <button 
                    v-if="game.is_joinable" 
                    class="join-btn"
                    @click="joinGame(game.game_id)"
                    :disabled="isJoining"
                  >
                    Join
                  </button>
                  <button 
                    v-else-if="game.is_completed" 
                    class="enter-btn"
                    @click="joinGame(game.game_id)"
                    :disabled="isJoining"
                  >
                    🏆 Enter
                  </button>
                  <span v-else class="full-badge">Full</span>
                </div>
              </div>
            </div>

            <div class="no-games" v-else>
              <p>🏜️ No active games found</p>
              <p class="hint">Create a new game to start exploring!</p>
            </div>
          </section>
        </div>

        <!-- Right Column: Player Stats & Leaderboard -->
        <div class="right-column">
          <!-- Player Stats Section -->
          <section class="stats-section" v-if="playerStats">
            <div class="stats-header">
              <h2>📊 Your Statistics</h2>
              <button 
                class="nickname-btn" 
                @click="generateNickname" 
                :disabled="isGeneratingNickname || (playerStats.monsters_killed || 0) < 1"
                :title="(playerStats.monsters_killed || 0) < 1 ? 'Kill monsters to unlock!' : 'Generate new nickname'"
              >
                <span v-if="isGeneratingNickname">🔄</span>
                <span v-else>✨ {{ playerStats.nickname ? 'Refresh' : 'Get'}} Title</span>
              </button>
            </div>
            <div class="stats-grid">
              <div class="stat-card highlight">
                <span class="stat-value">{{ playerStats.experience_earned || 0 }}</span>
                <span class="stat-label">⭐ XP</span>
              </div>
              <div class="stat-card">
                <span class="stat-value">{{ playerStats.monsters_killed || 0 }}</span>
                <span class="stat-label">⚔️ Kills</span>
              </div>
              <div class="stat-card">
                <span class="stat-value">{{ playerStats.rooms_visited || 0 }}</span>
                <span class="stat-label">🚪 Rooms</span>
              </div>
              <div class="stat-card">
                <span class="stat-value">{{ playerStats.deaths || 0 }}</span>
                <span class="stat-label">💀 Deaths</span>
              </div>
              <div class="stat-card">
                <span class="stat-value">{{ playerStats.total_games_played || 0 }}</span>
                <span class="stat-label">🎮 Games</span>
              </div>
              <div class="stat-card">
                <span class="stat-value">{{ playerStats.damage_dealt || 0 }}</span>
                <span class="stat-label">💥 Damage</span>
              </div>
            </div>
            
            <!-- Kill Breakdown -->
            <div class="kills-breakdown" v-if="Object.keys(playerStats.kills_by_type || {}).length > 0">
              <h3>🎯 Kill Breakdown</h3>
              <div class="kill-types">
                <div 
                  v-for="(count, type) in sortedKillsByType" 
                  :key="type"
                  class="kill-type"
                >
                  <span class="monster-type">{{ formatMonsterType(type) }}</span>
                  <span class="kill-count">×{{ count }}</span>
                </div>
              </div>
            </div>
          </section>

          <section class="leaderboard-section">
            <div class="leaderboard-header">
              <h2>🏆 Leaderboard</h2>
              <button class="refresh-btn" @click="fetchLeaderboard" :disabled="isLoadingLeaderboard">
                🔄
              </button>
            </div>
            <div class="leaderboard-content" v-if="leaderboard.length > 0">
              <div class="leaderboard-table">
                <div 
                  v-for="entry in leaderboard" 
                  :key="entry.token"
                  class="leaderboard-row"
                  :class="{ 'my-row': entry.token === playerToken }"
                >
                  <span class="rank">
                    <span v-if="entry.rank === 1">🥇</span>
                    <span v-else-if="entry.rank === 2">🥈</span>
                    <span v-else-if="entry.rank === 3">🥉</span>
                    <span v-else>#{{ entry.rank }}</span>
                  </span>
                  <div class="player-info">
                    <span class="name">{{ entry.full_title }}</span>
                    <div class="stats-line">
                      <span class="xp">{{ entry.experience }} XP</span>
                      <span class="kills">⚔️ {{ entry.kills }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="no-leaderboard" v-else>
              <p>No heroes yet. Be the first to slay monsters!</p>
            </div>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { usePlayerStore } from '../stores/playerStore'

const router = useRouter()
const playerStore = usePlayerStore()

// State
const games = ref([])
const leaderboard = ref([])
const customGameName = ref('')
const selectedMapSize = ref('medium')
const isLoading = ref(true)
const isLoadingLeaderboard = ref(false)
const isJoining = ref(false)
const isCreating = ref(false)
const isGeneratingNickname = ref(false)
const error = ref(null)

// Name editing state
const isEditingName = ref(false)
const editingName = ref('')
const nameInput = ref(null)

// Map size presets
const mapSizePresets = {
  small: { width: 60, height: 40, rooms: 6 },
  medium: { width: 100, height: 60, rooms: 10 },
  large: { width: 150, height: 80, rooms: 15 },
  huge: { width: 200, height: 100, rooms: 20 }
}

// Use playerToken from store
const playerToken = computed(() => playerStore.playerToken)
const playerStats = computed(() => playerStore.playerStats)
const fullTitle = computed(() => playerStore.fullTitle)

// Sorted kills by type for display
const sortedKillsByType = computed(() => {
  if (!playerStats.value?.kills_by_type) return {}
  const sorted = Object.entries(playerStats.value.kills_by_type)
    .sort(([,a], [,b]) => b - a)
  return Object.fromEntries(sorted)
})

// Format monster type for display
const formatMonsterType = (type) => {
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// Name editing functions
const startEditName = () => {
  editingName.value = playerStore.displayName || `Hero_${playerToken.value.substring(0, 6)}`
  isEditingName.value = true
  nextTick(() => {
    nameInput.value?.focus()
    nameInput.value?.select()
  })
}

const saveName = async () => {
  const newName = editingName.value.trim()
  if (newName && newName.length >= 2 && newName.length <= 30) {
    await playerStore.updateDisplayName(newName)
  }
  isEditingName.value = false
}

const cancelEditName = () => {
  isEditingName.value = false
}

// Generate nickname
const generateNickname = async () => {
  isGeneratingNickname.value = true
  try {
    await playerStore.generateNickname()
    // Refresh stats to get updated nickname
    await playerStore.fetchStats()
  } finally {
    isGeneratingNickname.value = false
  }
}

// Fetch available games
const fetchGames = async () => {
  isLoading.value = true
  error.value = null
  
  try {
    const response = await fetch('/api/lobby')
    if (!response.ok) {
      throw new Error('Failed to fetch games')
    }
    const data = await response.json()
    games.value = data.games || []
  } catch (e) {
    console.error('Error fetching games:', e)
    error.value = 'Failed to load games. Please try again.'
  } finally {
    isLoading.value = false
  }
}

// Fetch leaderboard
const fetchLeaderboard = async () => {
  isLoadingLeaderboard.value = true
  try {
    const response = await fetch('/api/leaderboard?limit=10')
    if (response.ok) {
      const data = await response.json()
      leaderboard.value = data.leaderboard || []
    }
  } catch (e) {
    console.error('Error fetching leaderboard:', e)
  } finally {
    isLoadingLeaderboard.value = false
  }
}

// Fetch player stats
const fetchPlayerStats = async () => {
  await playerStore.fetchStats()
}

// Quick join - find or create a joinable game
const quickJoin = async () => {
  isJoining.value = true
  error.value = null
  
  try {
    const response = await fetch('/api/games', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Player-Token': playerToken.value
      },
      body: JSON.stringify({})
    })
    
    if (!response.ok) {
      throw new Error('Failed to find/create game')
    }
    
    const data = await response.json()
    // Navigate to game
    router.push({ name: 'game', params: { gameId: data.game_id } })
  } catch (e) {
    console.error('Error quick joining:', e)
    error.value = 'Failed to join game. Please try again.'
  } finally {
    isJoining.value = false
  }
}

// Create new game with optional name and map size
const createGame = async () => {
  isCreating.value = true
  error.value = null
  
  try {
    const mapSize = mapSizePresets[selectedMapSize.value]
    const response = await fetch('/api/games', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Player-Token': playerToken.value
      },
      body: JSON.stringify({
        name: customGameName.value || null,
        auto_join: false,
        map_width: mapSize.width,
        map_height: mapSize.height,
        room_count: mapSize.rooms
      })
    })
    
    if (!response.ok) {
      throw new Error('Failed to create game')
    }
    
    const data = await response.json()
    customGameName.value = ''
    // Navigate to game
    router.push({ name: 'game', params: { gameId: data.game_id } })
  } catch (e) {
    console.error('Error creating game:', e)
    error.value = 'Failed to create game. Please try again.'
  } finally {
    isCreating.value = false
  }
}

// Join specific game
const joinGame = async (gameId) => {
  isJoining.value = true
  error.value = null
  
  try {
    const response = await fetch(`/api/games/${gameId}/join`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Player-Token': playerToken.value
      }
    })
    
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to join game')
    }
    
    // Navigate to game
    router.push({ name: 'game', params: { gameId } })
  } catch (e) {
    console.error('Error joining game:', e)
    error.value = e.message || 'Failed to join game. Please try again.'
  } finally {
    isJoining.value = false
  }
}

// Auto-refresh interval
let refreshInterval = null

// Initialize on mount
onMounted(() => {
  fetchGames()
  fetchPlayerStats()
  fetchLeaderboard()
  
  // Auto-refresh every 10 seconds
  refreshInterval = setInterval(() => {
    fetchGames()
    fetchLeaderboard()
  }, 10000)
})

// Cleanup on unmount
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.lobby-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #ecf0f1;
}

.header {
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #ffd700;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.5);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.header h1 {
  font-size: 1.8rem;
  color: #ffd700;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.back-btn {
  background: rgba(255, 255, 255, 0.1);
  color: #ecf0f1;
  border: 1px solid #555;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  text-decoration: none;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: #3498db;
}

.player-token {
  background: #1a1a2e;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-family: monospace;
  font-size: 0.9rem;
  color: #3498db;
  border: 1px solid #3498db;
}

.lobby-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

/* Two Column Layout */
.two-column-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 2rem;
  align-items: start;
}

.left-column {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.right-column {
  position: sticky;
  top: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.right-column .leaderboard-section {
  margin-bottom: 0;
}

.right-column .stats-section {
  margin-bottom: 0;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #333;
  border-top: 4px solid #ffd700;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Error State */
.error-state {
  text-align: center;
  padding: 2rem;
}

.error-message {
  color: #e74c3c;
  margin-bottom: 1rem;
}

.retry-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  background: #c0392b;
}

/* Sections */
section {
  background: rgba(44, 62, 80, 0.5);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid #444;
}

.left-column section {
  margin-bottom: 0;
}

section h2 {
  font-size: 1.3rem;
  color: #ffd700;
  margin-bottom: 0.5rem;
}

.section-desc {
  color: #95a5a6;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

/* Quick Join Section */
.quick-join-section {
  text-align: center;
  background: linear-gradient(135deg, rgba(39, 174, 96, 0.2) 0%, rgba(46, 204, 113, 0.1) 100%);
  border-color: #27ae60;
}

.quick-join-btn {
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
  color: white;
  border: none;
  padding: 1rem 3rem;
  border-radius: 10px;
  font-size: 1.2rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(39, 174, 96, 0.4);
}

.quick-join-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(39, 174, 96, 0.6);
}

.quick-join-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Create Section */
.create-form {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
}

.game-name-input {
  flex: 1;
  min-width: 200px;
  background: #1a1a2e;
  border: 1px solid #555;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  color: #ecf0f1;
  font-size: 1rem;
}

.game-name-input::placeholder {
  color: #666;
}

.game-name-input:focus {
  outline: none;
  border-color: #3498db;
}

.map-size-options {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.size-label {
  color: #95a5a6;
  font-size: 0.9rem;
  white-space: nowrap;
}

.size-select {
  background: #1a1a2e;
  border: 1px solid #555;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  color: #ecf0f1;
  font-size: 0.9rem;
  cursor: pointer;
  min-width: 180px;
}

.size-select:focus {
  outline: none;
  border-color: #3498db;
}

.size-select option {
  background: #1a1a2e;
  color: #ecf0f1;
}

.create-btn {
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.create-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #8e44ad 0%, #7d3c98 100%);
}

.create-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Games Section */
.games-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.games-header h2 {
  margin-bottom: 0;
}

.refresh-btn {
  background: rgba(52, 152, 219, 0.2);
  color: #3498db;
  border: 1px solid #3498db;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(52, 152, 219, 0.4);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.games-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.game-card {
  background: #1a1a2e;
  border-radius: 10px;
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #333;
  transition: all 0.2s ease;
}

.game-card.joinable {
  border-color: #27ae60;
}

.game-card.joinable:hover {
  background: #1a2a3a;
  border-color: #2ecc71;
}

.game-card.completed {
  border-color: #f39c12;
}

.game-card.completed:hover {
  background: #2a2a1a;
  border-color: #f1c40f;
}

.game-card.full {
  opacity: 0.7;
}

.game-name {
  font-size: 1.1rem;
  color: #ffd700;
  margin-bottom: 0.25rem;
}

.game-meta {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.25rem;
}

.player-count {
  color: #3498db;
  font-size: 0.9rem;
}

.game-status {
  color: #2ecc71;
  font-size: 0.9rem;
}

.game-status.completed {
  color: #95a5a6;
}

.game-id {
  font-size: 0.75rem;
  color: #666;
  font-family: monospace;
}

.join-btn {
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
  color: white;
  border: none;
  padding: 0.5rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: bold;
  transition: all 0.2s ease;
}

.join-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
}

.join-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.full-badge {
  background: #7f8c8d;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.9rem;
}

.enter-btn {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  color: white;
  border: none;
  padding: 0.5rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: bold;
  transition: all 0.2s ease;
}

.enter-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);
}

.enter-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.no-games {
  text-align: center;
  padding: 2rem;
  color: #95a5a6;
}

.no-games .hint {
  font-size: 0.9rem;
  margin-top: 0.5rem;
  color: #666;
}

/* Header Player Info */
.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.player-info {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.name-edit-container {
  position: relative;
}

.player-name {
  cursor: pointer;
  font-size: 1rem;
  color: #ffd700;
  padding: 0.5rem 1rem;
  background: rgba(255, 215, 0, 0.1);
  border-radius: 8px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.player-name:hover {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.2);
}

.edit-hint {
  opacity: 0;
  font-size: 0.8rem;
  transition: opacity 0.2s ease;
}

.player-name:hover .edit-hint {
  opacity: 1;
}

.name-input {
  background: #1a1a2e;
  border: 2px solid #ffd700;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  color: #ffd700;
  font-size: 1rem;
  min-width: 200px;
}

.name-input:focus {
  outline: none;
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
}

.player-xp {
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.3) 0%, rgba(142, 68, 173, 0.2) 100%);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-weight: bold;
  color: #e8a2ff;
  border: 1px solid #9b59b6;
}

/* Leaderboard Section */
.leaderboard-section {
  background: linear-gradient(135deg, rgba(241, 196, 15, 0.1) 0%, rgba(243, 156, 18, 0.05) 100%);
  border-color: #f1c40f;
}

.leaderboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.leaderboard-header h2 {
  margin-bottom: 0;
}

.leaderboard-content {
  max-height: 350px;
  overflow-y: auto;
}

.leaderboard-table {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.leaderboard-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(26, 26, 46, 0.8);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border: 1px solid #333;
  transition: all 0.2s ease;
}

.leaderboard-row:hover {
  background: rgba(26, 26, 46, 0.95);
  border-color: #555;
}

.leaderboard-row.my-row {
  background: rgba(52, 152, 219, 0.2);
  border-color: #3498db;
}

.leaderboard-row .rank {
  font-size: 1.2rem;
  font-weight: bold;
  text-align: center;
  color: #95a5a6;
  min-width: 40px;
}

.leaderboard-row .player-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.leaderboard-row .name {
  font-weight: 500;
  color: #ecf0f1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.leaderboard-row .stats-line {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
}

.leaderboard-row .xp {
  color: #e8a2ff;
  font-weight: bold;
}

.leaderboard-row .kills {
  color: #e74c3c;
}

.no-leaderboard {
  text-align: center;
  padding: 2rem;
  color: #95a5a6;
}

/* Stats Section */
.stats-section h2 {
  margin-bottom: 1rem;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.stats-header h2 {
  margin-bottom: 0;
}

.nickname-btn {
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s ease;
}

.nickname-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #8e44ad 0%, #7d3c98 100%);
  transform: translateY(-1px);
}

.nickname-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.stat-card {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
  border: 1px solid #333;
}

.stat-card.highlight {
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.2) 0%, rgba(142, 68, 173, 0.1) 100%);
  border-color: #9b59b6;
}

.stat-card.highlight .stat-value {
  color: #e8a2ff;
}

.stat-value {
  display: block;
  font-size: 1.8rem;
  font-weight: bold;
  color: #3498db;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.85rem;
  color: #95a5a6;
}

/* Kills Breakdown */
.kills-breakdown {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #444;
}

.kills-breakdown h3 {
  font-size: 1rem;
  color: #e74c3c;
  margin-bottom: 0.75rem;
}

.kill-types {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.kill-type {
  background: rgba(231, 76, 60, 0.15);
  border: 1px solid rgba(231, 76, 60, 0.3);
  padding: 0.4rem 0.75rem;
  border-radius: 20px;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.kill-type .monster-type {
  color: #ecf0f1;
}

.kill-type .kill-count {
  color: #e74c3c;
  font-weight: bold;
}

/* Responsive */
@media (max-width: 1024px) {
  .two-column-layout {
    grid-template-columns: 1fr;
  }
  
  .right-column {
    position: static;
    order: -1; /* Leaderboard first on mobile */
  }
}

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
  
  .header-left, .header-right {
    flex-direction: column;
  }
  
  .player-info {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .lobby-content {
    padding: 1rem;
  }
  
  .create-form {
    flex-direction: column;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .leaderboard-row {
    font-size: 0.9rem;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
  }
  
  .leaderboard-row .rank {
    min-width: 32px;
    font-size: 1rem;
  }
  
  .leaderboard-row .stats-line {
    gap: 0.75rem;
    font-size: 0.8rem;
  }
  
  .game-card {
    flex-direction: column;
    gap: 1rem;
    text-align: center;
  }
}
</style>
