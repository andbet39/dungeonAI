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
  font-size: 0.9rem;
  color: #ffd700;
  margin-bottom: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgba(255, 215, 0, 0.3);
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
  font-weight: 700;
}

.controls-info {
  font-size: 0.7rem;
  color: #c5d0dc;
  line-height: 1.6;
}

.controls-info p {
  margin-bottom: 0.4rem;
}

kbd {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 4px;
  padding: 0.15rem 0.35rem;
  font-family: monospace;
  font-size: 0.65rem;
  color: #ffd700;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  transition: all 0.2s ease;
}

kbd:hover {
  border-color: rgba(255, 215, 0, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.4);
}
</style>
