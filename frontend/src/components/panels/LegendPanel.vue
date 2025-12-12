<template>
  <section class="legend-section">
    <h2>Legend</h2>
    <div class="legend-grid">
      <div 
        v-for="item in legendItems" 
        :key="item.label" 
        class="legend-item"
      >
        <span class="tile-char" :style="{ color: item.color }">{{ item.char }}</span> {{ item.label }}
      </div>
    </div>
  </section>
</template>

<script>
import { TILE_LEGEND } from '../../constants/tiles'

export default {
  name: 'LegendPanel',
  setup() {
    return {
      legendItems: TILE_LEGEND
    }
  }
}
</script>

<style scoped>
.legend-section h2 {
  font-size: 0.9rem;
  color: #ffd700;
  margin-bottom: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
  font-weight: 700;
}

.legend-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.3rem;
  font-size: 0.65rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: #c5d0dc;
  padding: 0.2rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.legend-item:hover {
  background: rgba(255, 215, 0, 0.05);
  transform: translateX(2px);
}

.tile-char {
  font-family: monospace;
  font-size: 0.8rem;
  font-weight: 700;
  width: 1rem;
  text-align: center;
  text-shadow: 0 0 5px currentColor;
}
</style>
