<template>
  <div class="lobby-page">
    <header class="header">
      <div class="header-left">
        <h1>🗡️ DungeonAI Lobby</h1>
        <button v-if="isAdmin" @click="goToArena" class="admin-arena-btn">
          🤖 AI Arena
        </button>
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
          <button v-if="selectedProfile" @click="changeProfile" class="change-profile-btn">Change Profile</button>
        </div>
      </div>
    </header>

    <main class="lobby-content">
      <!-- Profile Selection -->
      <ProfileSelector 
        v-if="!selectedProfile" 
        @profile-selected="onProfileSelected"
      />

      <!-- Main Lobby Content (only show when profile is selected) -->
      <template v-else>
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

          <!-- Leaderboard Button Section -->
          <section class="leaderboard-action-section">
            <h2>🏆 Global Rankings</h2>
            <p class="section-desc">View the top heroes across all dungeons</p>
            <button class="view-leaderboard-btn" @click="showLeaderboardModal = true">
              <span class="btn-icon">🏆</span>
              <span class="btn-text">View Full Leaderboard</span>
            </button>
          </section>
        </div>
      </div>
      </template>
    </main>

    <!-- Leaderboard Modal -->
    <LeaderboardModal 
      :is-open="showLeaderboardModal" 
      :player-token="playerToken"
      @close="showLeaderboardModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePlayerStore } from '../stores/playerStore'
import ProfileSelector from '../components/ProfileSelector.vue'
import LeaderboardModal from '../components/LeaderboardModal.vue'

const router = useRouter()
const playerStore = usePlayerStore()

// State
const games = ref([])
const customGameName = ref('')
const selectedMapSize = ref('medium')
const isLoading = ref(false) // Start false, will be set to true when fetching
const isJoining = ref(false)
const isCreating = ref(false)
const isGeneratingNickname = ref(false)
const error = ref(null)
const showLeaderboardModal = ref(false)

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
const selectedProfile = computed(() => playerStore.selectedProfile)
const isAdmin = computed(() => playerStore.isAdmin)

// Navigation
const goToArena = () => {
  router.push('/arena')
}

// Profile selection handler
const onProfileSelected = async () => {
  console.log('Profile selected, fetching data...')
  console.log('Selected profile:', playerStore.selectedProfile)
  try {
    // Profile is now selected, fetch games and stats
    // Note: selectProfile already fetches stats, but we fetch again to ensure latest data
    await fetchGames()
    
    // Ensure stats are loaded (selectProfile should have already loaded them)
    if (!playerStore.playerStats) {
      console.log('Stats not loaded, fetching...')
      await playerStore.fetchStats()
    }
    
    console.log('Data fetched successfully, playerStats:', playerStore.playerStats)
    
    // Start auto-refresh now that profile is selected
    if (!refreshInterval) {
      refreshInterval = setInterval(() => {
        fetchGames()
      }, 10000)
    }
  } catch (err) {
    console.error('Error in onProfileSelected:', err)
    error.value = 'Failed to load lobby data'
  }
}

// Change profile - clear selected profile to show selector
const changeProfile = async () => {
  // Stop refresh interval
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
  
  // Clear selected profile (will show ProfileSelector and clear cookie)
  await playerStore.clearSelectedProfile()
  
  // Reset lobby state
  games.value = []
  error.value = null
}

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
    const response = await fetch('/api/lobby', {
      credentials: 'include'
    })
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

// Quick join - find or create a joinable game
const quickJoin = async () => {
  isJoining.value = true
  error.value = null
  
  try {
    const response = await fetch('/api/games', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
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
        'Content-Type': 'application/json'
      },
      credentials: 'include',
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
        'Content-Type': 'application/json'
      },
      credentials: 'include'
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
  // Only fetch if profile is already selected
  if (selectedProfile.value) {
    fetchGames()
    playerStore.fetchStats()
    
    // Auto-refresh every 10 seconds
    refreshInterval = setInterval(() => {
      fetchGames()
    }, 10000)
  }
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
  background: radial-gradient(ellipse at top, #1e2749 0%, #16213e 40%, #0f1419 100%);
  color: #ecf0f1;
  position: relative;
  overflow: hidden;
}

/* Animated Background Decorations */
.lobby-page::before {
  content: '';
  position: absolute;
  width: 400px;
  height: 400px;
  background: #ffd700;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.08;
  top: -100px;
  left: -100px;
  animation: float 20s infinite ease-in-out;
}

.lobby-page::after {
  content: '';
  position: absolute;
  width: 350px;
  height: 350px;
  background: #9b59b6;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.08;
  bottom: -100px;
  right: -100px;
  animation: float 25s infinite ease-in-out reverse;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  33% { transform: translate(30px, -30px); }
  66% { transform: translate(-20px, 20px); }
}

.header {
  background: rgba(20, 25, 40, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
  position: relative;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.header h1 {
  font-size: 1.8rem;
  color: #ffd700;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.admin-arena-btn {
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.2) 0%, rgba(142, 68, 173, 0.15) 100%);
  color: #9b59b6;
  border: 1px solid rgba(155, 89, 182, 0.4);
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.3s ease;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  white-space: nowrap;
}

.admin-arena-btn:hover {
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.3) 0%, rgba(142, 68, 173, 0.2) 100%);
  border-color: rgba(155, 89, 182, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(155, 89, 182, 0.3);
}

.back-btn {
  background: rgba(255, 215, 0, 0.1);
  color: #ffd700;
  border: 1px solid rgba(255, 215, 0, 0.3);
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.3s ease;
  cursor: pointer;
}

.back-btn:hover {
  background: rgba(255, 215, 0, 0.2);
  border-color: rgba(255, 215, 0, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 215, 0, 0.2);
}

.change-profile-btn {
  background: rgba(255, 215, 0, 0.1);
  color: #ffd700;
  border: 1px solid rgba(255, 215, 0, 0.3);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.3s ease;
  cursor: pointer;
  white-space: nowrap;
}

.change-profile-btn:hover {
  background: rgba(255, 215, 0, 0.2);
  border-color: rgba(255, 215, 0, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 215, 0, 0.2);
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
  padding: 1.5rem;
  position: relative;
  z-index: 1;
  height: calc(100vh - 80px);
  overflow-y: hidden;
}

/* Two Column Layout */
.two-column-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 1.5rem;
  align-items: start;
}

.left-column {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.right-column {
  position: sticky;
  top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-height: calc(100vh - 100px);
  overflow-y: hidden;
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
  background: rgba(20, 25, 40, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 215, 0, 0.2);
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
  font-weight: 500;
}

/* Error State */
.error-state {
  text-align: center;
  padding: 3rem;
  background: rgba(20, 25, 40, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.error-message {
  color: #fca5a5;
  margin-bottom: 1.5rem;
  font-size: 1.1rem;
  font-weight: 500;
}

.retry-btn {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  border: none;
  padding: 0.875rem 2rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 700;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
}

.retry-btn:hover {
  background: linear-gradient(135deg, #c0392b 0%, #a93226 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
}

/* Sections */
section {
  background: rgba(20, 25, 40, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 1.5rem;
  border: 1px solid rgba(255, 215, 0, 0.2);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

section:hover {
  border-color: rgba(255, 215, 0, 0.35);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), 0 0 30px rgba(255, 215, 0, 0.1);
}

.left-column section {
  margin-bottom: 0;
}

section h2 {
  font-size: 1.25rem;
  color: #ffd700;
  margin-bottom: 0.625rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  text-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
}

.section-desc {
  color: #a0aec0;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  font-weight: 400;
}

/* Quick Join Section */
.quick-join-section {
  text-align: center;
  background: linear-gradient(135deg, rgba(39, 174, 96, 0.15) 0%, rgba(46, 204, 113, 0.08) 100%);
  border-color: rgba(39, 174, 96, 0.4);
}

.quick-join-section:hover {
  border-color: rgba(39, 174, 96, 0.5);
}

.quick-join-btn {
  background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
  color: #fff;
  border: none;
  padding: 1rem 2.5rem;
  border-radius: 10px;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 6px 20px rgba(39, 174, 96, 0.35);
}

.quick-join-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(39, 174, 96, 0.5);
}

.quick-join-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
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
  background: rgba(15, 18, 30, 0.8);
  border: 1px solid rgba(255, 215, 0, 0.25);
  border-radius: 8px;
  padding: 0.875rem 1rem;
  color: #fff;
  font-size: 1rem;
  transition: all 0.3s;
}

.game-name-input::placeholder {
  color: #666;
}

.game-name-input:focus {
  outline: none;
  border-color: #ffd700;
  background: rgba(15, 18, 30, 0.95);
  box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.1);
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
  background: rgba(15, 18, 30, 0.8);
  border: 1px solid rgba(255, 215, 0, 0.25);
  border-radius: 8px;
  padding: 0.875rem 1rem;
  color: #ecf0f1;
  font-size: 0.9rem;
  cursor: pointer;
  min-width: 180px;
  transition: all 0.3s;
}

.size-select:focus {
  outline: none;
  border-color: #ffd700;
  box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.1);
}

.size-select option {
  background: #1a1a2e;
  color: #ecf0f1;
}

.create-btn {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  color: #1a1a2e;
  border: none;
  padding: 0.875rem 1.5rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
}

.create-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 215, 0, 0.5);
}

.create-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
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
  background: rgba(52, 152, 219, 0.15);
  color: #5dade2;
  border: 1px solid rgba(52, 152, 219, 0.4);
  padding: 0.625rem 1.125rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(52, 152, 219, 0.25);
  border-color: rgba(52, 152, 219, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.2);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.games-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.game-card {
  background: rgba(15, 18, 30, 0.7);
  border-radius: 12px;
  padding: 1.25rem 1.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid rgba(255, 215, 0, 0.2);
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.game-card.joinable {
  border-color: rgba(39, 174, 96, 0.4);
}

.game-card.joinable:hover {
  background: rgba(39, 174, 96, 0.1);
  border-color: rgba(39, 174, 96, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(39, 174, 96, 0.2);
}

.game-card.completed {
  border-color: rgba(243, 156, 18, 0.4);
}

.game-card.completed:hover {
  background: rgba(243, 156, 18, 0.1);
  border-color: rgba(243, 156, 18, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(243, 156, 18, 0.2);
}

.game-card.full {
  opacity: 0.6;
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
  padding: 0.625rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 700;
  transition: all 0.3s ease;
  box-shadow: 0 3px 12px rgba(39, 174, 96, 0.3);
}

.join-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
  transform: translateY(-2px);
  box-shadow: 0 5px 18px rgba(39, 174, 96, 0.4);
}

.join-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.full-badge {
  background: rgba(127, 140, 141, 0.3);
  color: #95a5a6;
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  border: 1px solid rgba(127, 140, 141, 0.4);
}

.enter-btn {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  color: white;
  border: none;
  padding: 0.625rem 1.5rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 700;
  transition: all 0.3s ease;
  box-shadow: 0 3px 12px rgba(243, 156, 18, 0.3);
}

.enter-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);
  transform: translateY(-2px);
  box-shadow: 0 5px 18px rgba(243, 156, 18, 0.4);
}

.enter-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.no-games {
  text-align: center;
  padding: 3rem 2rem;
  color: #a0aec0;
  background: rgba(15, 18, 30, 0.5);
  border-radius: 12px;
  border: 1px dashed rgba(255, 215, 0, 0.2);
}

.no-games p:first-child {
  font-size: 1.1rem;
  font-weight: 500;
}

.no-games .hint {
  font-size: 0.95rem;
  margin-top: 0.75rem;
  color: #718096;
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
  background: rgba(15, 18, 30, 0.95);
  border: 2px solid #ffd700;
  border-radius: 8px;
  padding: 0.625rem 1rem;
  color: #ffd700;
  font-size: 1rem;
  min-width: 200px;
  transition: all 0.3s;
  font-weight: 600;
}

.name-input:focus {
  outline: none;
  box-shadow: 0 0 0 4px rgba(255, 215, 0, 0.15);
}

.player-xp {
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.25) 0%, rgba(142, 68, 173, 0.15) 100%);
  backdrop-filter: blur(10px);
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 700;
  color: #e8a2ff;
  border: 1px solid rgba(155, 89, 182, 0.4);
  box-shadow: 0 2px 10px rgba(155, 89, 182, 0.2);
}

/* Leaderboard Action Section */
.leaderboard-action-section {
  background: linear-gradient(135deg, rgba(241, 196, 15, 0.15) 0%, rgba(243, 156, 18, 0.08) 100%);
  border-color: rgba(241, 196, 15, 0.4);
  text-align: center;
}

.leaderboard-action-section:hover {
  border-color: rgba(241, 196, 15, 0.5);
}

.view-leaderboard-btn {
  background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
  color: white;
  border: none;
  padding: 1rem 2rem;
  border-radius: 12px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 700;
  transition: all 0.3s ease;
  box-shadow: 0 6px 20px rgba(243, 156, 18, 0.35);
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
}

.view-leaderboard-btn:hover {
  background: linear-gradient(135deg, #e67e22 0%, #d35400 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(243, 156, 18, 0.5);
}

.view-leaderboard-btn .btn-icon {
  font-size: 1.5rem;
}

/* Stats Section */
.stats-section h2 {
  margin-bottom: 1rem;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.stats-header h2 {
  margin-bottom: 0;
}

.nickname-btn {
  background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%);
  color: white;
  border: none;
  padding: 0.625rem 1.125rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 3px 12px rgba(155, 89, 182, 0.3);
}

.nickname-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #8e44ad 0%, #7d3c98 100%);
  transform: translateY(-2px);
  box-shadow: 0 5px 18px rgba(155, 89, 182, 0.4);
}

.nickname-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.stat-card {
  background: rgba(15, 18, 30, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  padding: 1rem 0.75rem;
  text-align: center;
  border: 1px solid rgba(255, 215, 0, 0.2);
  transition: all 0.3s ease;
}

.stat-card:hover {
  border-color: rgba(255, 215, 0, 0.35);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.stat-card.highlight {
  background: linear-gradient(135deg, rgba(155, 89, 182, 0.25) 0%, rgba(142, 68, 173, 0.15) 100%);
  border-color: rgba(155, 89, 182, 0.5);
}

.stat-card.highlight:hover {
  border-color: rgba(155, 89, 182, 0.7);
  box-shadow: 0 6px 20px rgba(155, 89, 182, 0.3);
}

.stat-card.highlight .stat-value {
  color: #e8a2ff;
}

.stat-value {
  display: block;
  font-size: 1.75rem;
  font-weight: 700;
  color: #ffd700;
  margin-bottom: 0.375rem;
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
}

.stat-label {
  font-size: 0.8rem;
  color: #a0aec0;
  font-weight: 500;
}

/* Kills Breakdown */
.kills-breakdown {
  margin-top: 1.25rem;
  padding-top: 1.25rem;
  border-top: 1px solid rgba(255, 215, 0, 0.15);
}

.kills-breakdown h3 {
  font-size: 1.05rem;
  color: #e74c3c;
  margin-bottom: 1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  text-shadow: 0 0 10px rgba(231, 76, 60, 0.3);
}

.kill-types {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
}

.kill-type {
  background: rgba(231, 76, 60, 0.12);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(231, 76, 60, 0.35);
  padding: 0.5rem 0.875rem;
  border-radius: 20px;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.3s ease;
}

.kill-type:hover {
  background: rgba(231, 76, 60, 0.18);
  border-color: rgba(231, 76, 60, 0.5);
  transform: translateY(-1px);
}

.kill-type .monster-type {
  color: #ecf0f1;
  font-weight: 500;
}

.kill-type .kill-count {
  color: #e74c3c;
  font-weight: 700;
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
