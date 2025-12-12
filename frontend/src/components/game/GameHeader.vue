<template>
  <header class="header">
    <div class="header-left">
      <router-link to="/lobby" class="back-btn">← Lobby</router-link>
      <h1>🗡️ {{ gameName }}</h1>
    </div>
    <div class="header-right">
      <div class="world-position" v-if="myPlayer">
        📍 World: ({{ myPlayer.x }}, {{ myPlayer.y }})
      </div>
      <div class="connection-status" :class="{ connected: isConnected, disconnected: !isConnected }">
        {{ isConnected ? '● Connected' : '○ Disconnected' }}
      </div>
    </div>
  </header>
</template>

<script>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useGameStore } from '../../stores/gameStore'
import { usePlayerStore } from '../../stores/playerStore'
import { useSocketStore } from '../../stores/socketStore'

export default {
  name: 'GameHeader',
  setup() {
    const gameStore = useGameStore()
    const playerStore = usePlayerStore()
    const socketStore = useSocketStore()

    const { gameName } = storeToRefs(gameStore)
    const { myPlayer } = storeToRefs(playerStore)
    const { isConnected } = storeToRefs(socketStore)

    return {
      gameName,
      myPlayer,
      isConnected
    }
  }
}
</script>

<style scoped>
.header {
  background: rgba(20, 25, 40, 0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  padding: 0.75rem 1.5rem;
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
  gap: 1rem;
}

.header h1 {
  font-size: 1.4rem;
  color: #ffd700;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.back-btn {
  background: rgba(255, 215, 0, 0.1);
  color: #ffd700;
  border: 1px solid rgba(255, 215, 0, 0.3);
  padding: 0.5rem 1rem;
  border-radius: 8px;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: rgba(255, 215, 0, 0.2);
  border-color: rgba(255, 215, 0, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 215, 0, 0.2);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.world-position {
  background: rgba(15, 18, 30, 0.8);
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  font-family: monospace;
  font-size: 0.8rem;
  color: #5dade2;
  border: 1px solid rgba(52, 152, 219, 0.4);
  backdrop-filter: blur(10px);
}

.connection-status {
  padding: 0.4rem 0.8rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.connection-status.connected {
  background: rgba(39, 174, 96, 0.9);
  color: white;
  border: 1px solid rgba(39, 174, 96, 0.5);
  box-shadow: 0 0 15px rgba(39, 174, 96, 0.3);
}

.connection-status.disconnected {
  background: rgba(231, 76, 60, 0.9);
  color: white;
  border: 1px solid rgba(231, 76, 60, 0.5);
  box-shadow: 0 0 15px rgba(231, 76, 60, 0.3);
}
</style>
