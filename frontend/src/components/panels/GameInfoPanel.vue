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
  font-size: 0.9rem;
  color: #ffd700;
  margin-bottom: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
  font-weight: 700;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 0.35rem 0.4rem;
  border-bottom: 1px solid rgba(255, 215, 0, 0.1);
  border-radius: 4px;
  transition: all 0.2s ease;
}

.info-item:hover {
  background: rgba(255, 215, 0, 0.05);
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  color: #8e949e;
  font-size: 0.7rem;
  font-weight: 600;
}

.info-item .value {
  color: #ffd700;
  font-weight: 700;
  font-size: 0.7rem;
  text-shadow: 0 0 5px rgba(255, 215, 0, 0.2);
}
</style>
