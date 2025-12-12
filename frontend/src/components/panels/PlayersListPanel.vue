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
  font-size: 0.9rem;
  color: #ffd700;
  margin-bottom: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
  font-weight: 700;
}

.players-list {
  max-height: 150px;
  overflow-y: auto;
}

.players-list::-webkit-scrollbar {
  width: 6px;
}

.players-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
}

.players-list::-webkit-scrollbar-thumb {
  background: rgba(255, 215, 0, 0.3);
  border-radius: 3px;
}

.players-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 215, 0, 0.5);
}

.player-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem;
  margin-bottom: 0.3rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  border: 1px solid rgba(255, 215, 0, 0.15);
  transition: all 0.2s ease;
}

.player-item:hover {
  background: rgba(255, 215, 0, 0.05);
  border-color: rgba(255, 215, 0, 0.3);
  transform: translateX(2px);
}

.player-item.is-you {
  background: rgba(255, 215, 0, 0.1);
  border-color: rgba(255, 215, 0, 0.4);
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.2);
}

.player-symbol {
  font-size: 1.1rem;
  font-weight: 700;
  font-family: monospace;
  text-shadow: 0 0 8px currentColor;
}

.player-info {
  flex: 1;
}

.player-name {
  font-weight: 700;
  color: #ffd700;
  font-size: 0.75rem;
  text-shadow: 0 0 5px rgba(255, 215, 0, 0.2);
}

.player-pos {
  font-size: 0.65rem;
  color: #8e949e;
  margin-top: 0.1rem;
}
</style>
