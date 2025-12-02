<template>
  <transition name="room-fade">
    <div 
      class="room-description-overlay" 
      v-if="showRoomDescription && currentRoom" 
      @click="dismissRoomDescription"
    >
      <div class="room-description-card" @click.stop>
        <div class="room-icon">🚪</div>
        <h2 class="room-name">{{ currentRoom.name }}</h2>
        <p class="room-desc">{{ currentRoom.description }}</p>
        <div class="room-dismiss-hint">Click anywhere to dismiss</div>
      </div>
    </div>
  </transition>
</template>

<script>
import { storeToRefs } from 'pinia'
import { useGameStore } from '../../stores/gameStore'

export default {
  name: 'RoomDescriptionOverlay',
  setup() {
    const gameStore = useGameStore()
    const { currentRoom, showRoomDescription } = storeToRefs(gameStore)
    const { dismissRoomDescription } = gameStore

    return {
      currentRoom,
      showRoomDescription,
      dismissRoomDescription
    }
  }
}
</script>

<style scoped>
.room-description-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  cursor: pointer;
}

.room-description-card {
  background: linear-gradient(135deg, #2c3e50 0%, #1a1a2e 100%);
  border: 2px solid #ffd700;
  border-radius: 16px;
  padding: 2rem 3rem;
  max-width: 600px;
  text-align: center;
  box-shadow: 0 0 40px rgba(255, 215, 0, 0.3);
  cursor: default;
  animation: cardAppear 0.3s ease-out;
}

@keyframes cardAppear {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.room-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.room-name {
  font-size: 1.8rem;
  color: #ffd700;
  margin-bottom: 1rem;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.room-desc {
  font-size: 1.1rem;
  color: #bdc3c7;
  line-height: 1.6;
  font-style: italic;
  margin-bottom: 1.5rem;
}

.room-dismiss-hint {
  font-size: 0.85rem;
  color: #7f8c8d;
}

.room-fade-enter-active,
.room-fade-leave-active {
  transition: opacity 0.3s ease;
}

.room-fade-enter-from,
.room-fade-leave-to {
  opacity: 0;
}
</style>
