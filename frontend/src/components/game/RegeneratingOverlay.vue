<template>
  <div class="regenerating-overlay" v-if="isRegenerating">
    <div class="regenerating-content">
      <div class="regenerating-spinner"></div>
      <h2>Generating New Dungeon...</h2>
      <p>The ancient halls are reshaping themselves</p>
    </div>
  </div>
</template>

<script>
import { storeToRefs } from 'pinia'
import { useGameStore } from '../../stores/gameStore'

export default {
  name: 'RegeneratingOverlay',
  setup() {
    const gameStore = useGameStore()
    const { isRegenerating } = storeToRefs(gameStore)

    return {
      isRegenerating
    }
  }
}
</script>

<style scoped>
.regenerating-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.regenerating-content {
  text-align: center;
}

.regenerating-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #333;
  border-top: 4px solid #ffd700;
  border-radius: 50%;
  margin: 0 auto 1.5rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.regenerating-content h2 {
  color: #ffd700;
  margin-bottom: 0.5rem;
}

.regenerating-content p {
  color: #7f8c8d;
  font-style: italic;
}
</style>
