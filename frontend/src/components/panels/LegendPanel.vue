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
  font-size: 0.85rem;
  color: #9b59b6;
  margin-bottom: 0.3rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #444;
}

.legend-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.15rem;
  font-size: 0.6rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: #95a5a6;
}

.tile-char {
  font-family: monospace;
  font-size: 0.75rem;
  font-weight: bold;
  width: 0.9rem;
  text-align: center;
}
</style>
