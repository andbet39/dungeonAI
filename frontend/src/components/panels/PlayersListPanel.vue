<template>
  <section class="players-section">
    <h2>Players</h2>
    <div class="players-list">
      <div 
        v-for="player in playersList" 
        :key="player.id"
        class="player-item"
        :class="{ 'is-you': player.id === myPlayerId }"
      >
        <span class="player-symbol" :style="{ color: player.color }">{{ player.symbol }}</span>
        <div class="player-info">
          <div class="player-name">
            {{ player.id === myPlayerId ? 'You' : `Player ${player.id.substring(0, 4)}` }}
          </div>
          <div class="player-pos">Position: ({{ player.x }}, {{ player.y }})</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '../../stores/playerStore'

export default {
  name: 'PlayersListPanel',
  setup() {
    const playerStore = usePlayerStore()
    const { playersList, myPlayerId } = storeToRefs(playerStore)

    return {
      playersList,
      myPlayerId
    }
  }
}
</script>

<style scoped>
.players-section h2 {
  font-size: 0.85rem;
  color: #3498db;
  margin-bottom: 0.3rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #444;
}

.players-list {
  max-height: 100px;
  overflow-y: auto;
}

.player-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem;
  margin-bottom: 0.2rem;
  background: #1a1a1a;
  border-radius: 4px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.player-item:hover {
  background: #252525;
  border-color: #3498db;
}

.player-item.is-you {
  background: #2a3f5f;
  border-color: #3498db;
}

.player-symbol {
  font-size: 1rem;
  font-weight: bold;
  font-family: monospace;
}

.player-info {
  flex: 1;
}

.player-name {
  font-weight: bold;
  color: #ecf0f1;
  font-size: 0.7rem;
}

.player-pos {
  font-size: 0.6rem;
  color: #95a5a6;
}
</style>
