<template>
  <section class="room-section" v-if="currentRoom">
    <h2>📍 Current Room</h2>
    <div class="current-room-info">
      <div class="current-room-name">{{ currentRoom.name }}</div>
      <div class="current-room-desc">{{ currentRoom.description }}</div>
    </div>
  </section>
</template>

<script>
import { storeToRefs } from 'pinia'
import { useGameStore } from '../../stores/gameStore'

export default {
  name: 'CurrentRoomPanel',
  setup() {
    const gameStore = useGameStore()
    const { currentRoom } = storeToRefs(gameStore)

    return {
      currentRoom
    }
  }
}
</script>

<style scoped>
.room-section h2 {
  font-size: 0.85rem;
  color: #ffd700;
  margin-bottom: 0.3rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #444;
}

.current-room-info {
  background: #1a1a2e;
  border-radius: 6px;
  padding: 0.4rem;
  border-left: 2px solid #ffd700;
}

.current-room-name {
  font-weight: bold;
  color: #ffd700;
  margin-bottom: 0.2rem;
  font-size: 0.8rem;
}

.current-room-desc {
  color: #bdc3c7;
  font-size: 0.65rem;
  line-height: 1.3;
  font-style: italic;
}
</style>
