<template>
  <section class="info-section">
    <h2>Game Info</h2>
    <div class="info-item">
      <span class="label">Your ID:</span>
      <span class="value">{{ myPlayerId ? myPlayerId.substring(0, 8) : 'Connecting...' }}</span>
    </div>
    <div class="info-item">
      <span class="label">Players Online:</span>
      <span class="value">{{ playerCount }}</span>
    </div>
    <div class="info-item">
      <span class="label">Monsters:</span>
      <span class="value">{{ monsterCount }}</span>
    </div>
    <div class="info-item">
      <span class="label">Map Size:</span>
      <span class="value">{{ mapWidth }} × {{ mapHeight }}</span>
    </div>
    <div class="info-item">
      <span class="label">Rooms Visited:</span>
      <span class="value">{{ visitedRoomsCount }} / {{ totalRoomsCount }}</span>
    </div>
    <div class="info-item">
      <span class="label">Viewport:</span>
      <span class="value">{{ viewportWidth }} × {{ viewportHeight }}</span>
    </div>
  </section>
</template>

<script>
import { storeToRefs } from 'pinia'
import { useGameStore } from '../../stores/gameStore'
import { usePlayerStore } from '../../stores/playerStore'

export default {
  name: 'GameInfoPanel',
  setup() {
    const gameStore = useGameStore()
    const playerStore = usePlayerStore()

    const { monsterCount, mapWidth, mapHeight, viewportWidth, viewportHeight, visitedRoomsCount, totalRoomsCount } = storeToRefs(gameStore)
    const { myPlayerId, playerCount } = storeToRefs(playerStore)

    return {
      myPlayerId,
      playerCount,
      monsterCount,
      mapWidth,
      mapHeight,
      viewportWidth,
      viewportHeight,
      visitedRoomsCount,
      totalRoomsCount
    }
  }
}
</script>

<style scoped>
.info-section h2 {
  font-size: 0.85rem;
  color: #3498db;
  margin-bottom: 0.3rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #444;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.2rem 0;
  border-bottom: 1px solid #333;
}

.info-item .label {
  color: #95a5a6;
  font-size: 0.7rem;
}

.info-item .value {
  color: #ecf0f1;
  font-weight: bold;
  font-size: 0.7rem;
}
</style>
