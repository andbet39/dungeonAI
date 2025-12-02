<template>
  <section class="controls-section">
    <h2>Controls</h2>
    <div class="controls-info">
      <p><kbd>↑</kbd> <kbd>↓</kbd> <kbd>←</kbd> <kbd>→</kbd> or <kbd>HJKL</kbd> - Move</p>
      <p><kbd>Space</kbd> or <kbd>E</kbd> - Interact</p>
    </div>
  </section>
</template>

<script>
export default {
  name: 'ControlsPanel'
}
</script>

<style scoped>
.controls-section h2 {
  font-size: 0.85rem;
  color: #f39c12;
  margin-bottom: 0.3rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #444;
}

.controls-info {
  font-size: 0.65rem;
  color: #95a5a6;
  line-height: 1.5;
}

.controls-info p {
  margin-bottom: 0.2rem;
}

kbd {
  background: #1a1a1a;
  border: 1px solid #555;
  border-radius: 2px;
  padding: 0.1rem 0.25rem;
  font-family: monospace;
  font-size: 0.6rem;
  color: #ecf0f1;
}
</style>
