<template>
  <transition name="completion-fade">
    <div class="game-completed-overlay" v-if="gameStore.isGameCompleted && !dismissed">
      <div class="completion-content">
        <div class="completion-icon">🏆</div>
        <h1 class="completion-title">DUNGEON CLEARED!</h1>
        <p class="completion-message">
          Congratulations! You have explored all rooms and defeated all monsters!
        </p>
        <div class="completion-stats">
          <div class="stat-item">
            <span class="stat-icon">🗺️</span>
            <span class="stat-label">Rooms Explored</span>
            <span class="stat-value">{{ gameStore.visitedRoomsCount }} / {{ gameStore.totalRoomsCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-icon">⚔️</span>
            <span class="stat-label">Monsters Remaining</span>
            <span class="stat-value">{{ gameStore.monsterCount }}</span>
          </div>
        </div>
        <div class="completion-actions">
          <button class="btn-lobby" @click="goToLobby">
            🏠 Return to Lobby
          </button>
          <button class="btn-continue" @click="dismiss">
            🎮 Continue Exploring
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../../stores/gameStore'

const router = useRouter()
const gameStore = useGameStore()

const dismissed = ref(false)

// Reset dismissed state when completion status changes
watch(() => gameStore.isGameCompleted, (newVal) => {
  if (newVal) {
    dismissed.value = false
  }
})

const dismiss = () => {
  dismissed.value = true
}

const goToLobby = () => {
  router.push('/')
}
</script>

<style scoped>
.game-completed-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 3000;
  animation: overlayAppear 0.5s ease-out;
}

@keyframes overlayAppear {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.completion-content {
  text-align: center;
  padding: 3rem 4rem;
  background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
  border: 3px solid #ffd700;
  border-radius: 20px;
  box-shadow: 0 0 60px rgba(255, 215, 0, 0.4), inset 0 0 30px rgba(255, 215, 0, 0.1);
  animation: contentBounce 0.6s ease-out;
  max-width: 600px;
}

@keyframes contentBounce {
  0% {
    opacity: 0;
    transform: scale(0.5);
  }
  50% {
    transform: scale(1.05);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.completion-icon {
  font-size: 5rem;
  margin-bottom: 1rem;
  animation: trophyGlow 2s ease-in-out infinite;
}

@keyframes trophyGlow {
  0%, 100% {
    text-shadow: 0 0 20px rgba(255, 215, 0, 0.8), 0 0 40px rgba(255, 215, 0, 0.4);
    transform: scale(1);
  }
  50% {
    text-shadow: 0 0 40px rgba(255, 215, 0, 1), 0 0 80px rgba(255, 215, 0, 0.6);
    transform: scale(1.1);
  }
}

.completion-title {
  font-size: 2.5rem;
  font-weight: bold;
  color: #ffd700;
  text-transform: uppercase;
  letter-spacing: 4px;
  margin-bottom: 1rem;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
}

.completion-message {
  font-size: 1.2rem;
  color: #bdc3c7;
  margin-bottom: 2rem;
  line-height: 1.6;
}

.completion-stats {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 12px;
  border: 1px solid rgba(255, 215, 0, 0.3);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.stat-icon {
  font-size: 1.5rem;
}

.stat-label {
  font-size: 0.85rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stat-value {
  font-size: 1.3rem;
  font-weight: bold;
  color: #fff;
}

.completion-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.btn-lobby,
.btn-continue {
  padding: 1rem 2rem;
  font-size: 1.1rem;
  font-weight: bold;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-lobby {
  background: linear-gradient(135deg, #555 0%, #333 100%);
  color: #ccc;
}

.btn-lobby:hover {
  transform: translateY(-3px);
  background: linear-gradient(135deg, #666 0%, #444 100%);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
}

.btn-continue {
  background: linear-gradient(135deg, #f1c40f 0%, #f39c12 100%);
  color: #1a1a1a;
  box-shadow: 0 4px 20px rgba(241, 196, 15, 0.4);
}

.btn-continue:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 30px rgba(241, 196, 15, 0.6);
}

/* Transition */
.completion-fade-enter-active,
.completion-fade-leave-active {
  transition: opacity 0.5s ease;
}

.completion-fade-enter-from,
.completion-fade-leave-to {
  opacity: 0;
}
</style>
