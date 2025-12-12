<template>
  <div class="profile-selector-overlay">
    <div class="profile-selector-card">
      <div class="selector-header">
        <h2>⚔️ Select Your Hero</h2>
        <p>Choose a profile or create a new one (max 4 profiles)</p>
        <button class="logout-btn" @click="handleLogout" title="Logout">
          🚪 Logout
        </button>
      </div>

      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Loading profiles...</p>
      </div>

      <div v-else-if="error" class="error-state">
        <p class="error-message">{{ error }}</p>
        <button @click="loadProfiles" class="retry-btn">Retry</button>
      </div>

      <div v-else class="profiles-content">
        <!-- Existing Profiles -->
        <div class="profiles-grid" v-if="profiles.length > 0">
          <div 
            v-for="profile in profiles" 
            :key="profile.token"
            class="profile-card"
            @click="selectProfile(profile.token)"
          >
            <div class="profile-icon">🎮</div>
            <div class="profile-info">
              <h3 class="profile-name">{{ profile.display_name }}</h3>
              <p class="profile-nickname" v-if="profile.nickname">{{ profile.nickname }}</p>
              <div class="profile-stats">
                <span>⭐ {{ profile.experience_earned }} XP</span>
                <span>⚔️ {{ profile.monsters_killed }} kills</span>
                <span>🎮 {{ profile.total_games_played }} games</span>
              </div>
              <div class="profile-meta">
                <span v-if="profile.current_game_id" class="in-game-badge">
                  🎲 In Game
                </span>
              </div>
            </div>
            <div class="select-arrow">→</div>
          </div>
        </div>

        <div v-else class="no-profiles">
          <p>🌟 No profiles yet!</p>
          <p class="hint">Create your first hero to begin your adventure</p>
        </div>

        <!-- Create New Profile -->
        <div class="create-profile-section" v-if="profiles.length < maxProfiles">
          <div v-if="!showCreateForm" class="create-profile-prompt">
            <button @click="showCreateForm = true" class="create-profile-btn">
              ✨ Create New Profile
            </button>
            <p class="profile-count">{{ profiles.length }} / {{ maxProfiles }} profiles</p>
          </div>

          <div v-else class="create-profile-form">
            <h3>Create New Hero</h3>
            <input
              ref="nameInput"
              v-model="newProfileName"
              type="text"
              placeholder="Enter hero name"
              maxlength="30"
              class="name-input"
              @keyup.enter="createProfile"
              @keyup.escape="cancelCreate"
            />
            <div class="form-actions">
              <button @click="createProfile" :disabled="!newProfileName.trim() || creating" class="submit-btn">
                <span v-if="creating">Creating...</span>
                <span v-else>Create</span>
              </button>
              <button @click="cancelCreate" class="cancel-btn">Cancel</button>
            </div>
          </div>
        </div>

        <div v-else class="max-profiles-message">
          <p>🎭 Maximum profiles reached ({{ maxProfiles }})</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, onBeforeUnmount } from 'vue'
import { usePlayerStore } from '../stores/playerStore'
import { useRouter } from 'vue-router'

const emit = defineEmits(['profile-selected'])

const playerStore = usePlayerStore()
const router = useRouter()

const profiles = ref([])
const maxProfiles = ref(4)
const loading = ref(false)
const error = ref('')
const showCreateForm = ref(false)
const newProfileName = ref('')
const creating = ref(false)
const nameInput = ref(null)

onMounted(async () => {
  await loadProfiles()
})

async function loadProfiles() {
  loading.value = true
  error.value = ''
  try {
    const data = await playerStore.fetchProfiles()
    profiles.value = data
    maxProfiles.value = 4
  } catch (err) {
    error.value = 'Failed to load profiles'
    console.error(err)
  } finally {
    loading.value = false
  }
}

async function selectProfile(token) {
  loading.value = true
  error.value = ''
  try {
    // First emit the event to parent
    emit('profile-selected')
    console.log('Profile selected event emitted')
    
    // Then select the profile (which will cause this component to unmount)
    await playerStore.selectProfile(token)
  } catch (err) {
    error.value = 'Failed to select profile'
    console.error(err)
  } finally {
    loading.value = false
  }
}

async function createProfile() {
  if (!newProfileName.value.trim()) return
  
  creating.value = true
  error.value = ''
  try {
    await playerStore.createProfile(newProfileName.value.trim())
    newProfileName.value = ''
    showCreateForm.value = false
    await loadProfiles()
    // Profile is auto-selected after creation
    emit('profile-selected')
  } catch (err) {
    error.value = err.message || 'Failed to create profile'
    console.error(err)
  } finally {
    creating.value = false
  }
}

function cancelCreate() {
  showCreateForm.value = false
  newProfileName.value = ''
  error.value = ''
}

async function handleLogout() {
  await playerStore.logout()
  router.push('/')
}

// Auto-focus name input when shown
watch(() => showCreateForm.value, async (shown) => {
  if (shown) {
    await nextTick()
    nameInput.value?.focus()
  }
})
</script>

<style scoped>
.profile-selector-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 2rem;
}

.profile-selector-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 16px;
  padding: 2.5rem;
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
}

.selector-header {
  text-align: center;
  margin-bottom: 2rem;
  position: relative;
}

.selector-header h2 {
  color: #ffd700;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.selector-header p {
  color: #aaa;
  font-size: 0.95rem;
}

.logout-btn {
  position: absolute;
  top: 0;
  right: 0;
  background: rgba(255, 50, 50, 0.2);
  border: 1px solid rgba(255, 50, 50, 0.5);
  color: #ff6b6b;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: rgba(255, 50, 50, 0.3);
  transform: translateY(-2px);
}

.loading-state, .error-state {
  text-align: center;
  padding: 3rem;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 215, 0, 0.2);
  border-top-color: #ffd700;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.profiles-grid {
  display: grid;
  gap: 1rem;
  margin-bottom: 2rem;
}

.profile-card {
  background: rgba(30, 30, 50, 0.6);
  border: 2px solid rgba(255, 215, 0, 0.2);
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  cursor: pointer;
  transition: all 0.3s;
}

.profile-card:hover {
  border-color: #ffd700;
  background: rgba(30, 30, 50, 0.8);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 215, 0, 0.2);
}

.profile-icon {
  font-size: 3rem;
  flex-shrink: 0;
}

.profile-info {
  flex: 1;
}

.profile-name {
  color: #ffd700;
  font-size: 1.3rem;
  margin-bottom: 0.25rem;
}

.profile-nickname {
  color: #9b59b6;
  font-size: 0.9rem;
  font-style: italic;
  margin-bottom: 0.5rem;
}

.profile-stats {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: 0.85rem;
  color: #aaa;
}

.profile-meta {
  margin-top: 0.5rem;
}

.in-game-badge {
  background: rgba(46, 204, 113, 0.2);
  border: 1px solid rgba(46, 204, 113, 0.5);
  color: #2ecc71;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.select-arrow {
  font-size: 2rem;
  color: #ffd700;
  opacity: 0.5;
  transition: all 0.3s;
}

.profile-card:hover .select-arrow {
  opacity: 1;
  transform: translateX(5px);
}

.no-profiles {
  text-align: center;
  padding: 3rem;
  color: #aaa;
}

.no-profiles p:first-child {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.hint {
  font-size: 0.9rem;
  color: #777;
}

.create-profile-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 215, 0, 0.2);
}

.create-profile-prompt {
  text-align: center;
}

.create-profile-btn {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  border-radius: 8px;
  padding: 1rem 2rem;
  color: #1a1a2e;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.create-profile-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 215, 0, 0.4);
}

.profile-count {
  margin-top: 1rem;
  color: #aaa;
  font-size: 0.9rem;
}

.create-profile-form {
  background: rgba(30, 30, 50, 0.6);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 12px;
  padding: 2rem;
}

.create-profile-form h3 {
  color: #ffd700;
  margin-bottom: 1rem;
}

.name-input {
  width: 100%;
  background: rgba(20, 20, 40, 0.8);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 6px;
  padding: 0.75rem;
  color: #fff;
  font-size: 1rem;
  margin-bottom: 1rem;
}

.name-input:focus {
  outline: none;
  border-color: #ffd700;
}

.form-actions {
  display: flex;
  gap: 1rem;
}

.submit-btn, .cancel-btn, .retry-btn {
  flex: 1;
  padding: 0.75rem;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  color: #1a1a2e;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-btn {
  background: rgba(255, 50, 50, 0.2);
  border: 1px solid rgba(255, 50, 50, 0.5);
  color: #ff6b6b;
}

.retry-btn {
  background: rgba(255, 215, 0, 0.2);
  border: 1px solid rgba(255, 215, 0, 0.5);
  color: #ffd700;
}

.submit-btn:hover:not(:disabled), .cancel-btn:hover, .retry-btn:hover {
  transform: translateY(-2px);
}

.max-profiles-message {
  text-align: center;
  padding: 2rem;
  color: #aaa;
  font-size: 0.95rem;
}

.error-message {
  background: rgba(255, 50, 50, 0.2);
  border: 1px solid rgba(255, 50, 50, 0.5);
  border-radius: 6px;
  padding: 1rem;
  color: #ff6b6b;
  margin-bottom: 1rem;
}
</style>
