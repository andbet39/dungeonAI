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
  font-size: 0.9rem;
  color: #ffd700;
  margin-bottom: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
  font-weight: 700;
}

.current-room-info {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  padding: 0.6rem;
  border-left: 3px solid #ffd700;
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.1);
  transition: all 0.3s ease;
}

.current-room-info:hover {
  border-left-color: rgba(255, 215, 0, 0.8);
  box-shadow: 0 0 20px rgba(255, 215, 0, 0.2);
}

.current-room-name {
  font-weight: 700;
  color: #ffd700;
  margin-bottom: 0.4rem;
  font-size: 0.85rem;
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
}

.current-room-desc {
  color: #c5d0dc;
  font-size: 0.7rem;
  line-height: 1.5;
  font-style: italic;
}
</style>
