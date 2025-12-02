<template>
  <div class="game-canvas-wrapper">
    <div id="game" ref="gameCanvas"></div>
  </div>
</template>

<script>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import * as ROT from 'rot-js'
import { useGameStore } from '../../stores/gameStore'
import { usePlayerStore } from '../../stores/playerStore'
import { useEventLogStore } from '../../stores/eventLogStore'
import { TILE, TILE_RENDER } from '../../constants/tiles'

export default {
  name: 'GameCanvas',
  setup() {
    const gameStore = useGameStore()
    const playerStore = usePlayerStore()
    const eventLogStore = useEventLogStore()

    const { gameState, actualViewportWidth, actualViewportHeight } = storeToRefs(gameStore)
    const { players } = storeToRefs(playerStore)

    const gameCanvas = ref(null)
    let display = null

    /**
     * Setup or reinitialize the ROT.js display
     */
    function setupDisplay() {
      if (!gameState.value) return

      // Remove old display if exists
      if (display && gameCanvas.value) {
        const oldContainer = display.getContainer()
        if (oldContainer && oldContainer.parentNode) {
          oldContainer.parentNode.removeChild(oldContainer)
        }
      }

      // Create new display
      display = new ROT.Display({
        width: actualViewportWidth.value,
        height: actualViewportHeight.value,
        fontSize: 24,
        fontFamily: 'monospace',
        bg: '#000',
        fg: '#fff'
      })

      // Attach to DOM
      if (gameCanvas.value) {
        gameCanvas.value.appendChild(display.getContainer())
      }

      eventLogStore.addLog('Game display initialized', 'system')
    }

    /**
     * Draw a single tile
     */
    function drawTile(x, y, tile) {
      const config = TILE_RENDER[tile] || TILE_RENDER[TILE.FLOOR]
      display.draw(x, y, config.char, config.fg, config.bg)
    }

    /**
     * Render the map tiles
     */
    function renderMap() {
      if (!gameState.value || !gameState.value.tiles) return

      const tiles = gameState.value.tiles
      const height = tiles.length
      const width = height > 0 ? tiles[0].length : 0

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          drawTile(x, y, tiles[y][x])
        }
      }
    }

    /**
     * Render all players
     */
    function renderPlayers() {
      if (!gameState.value?.players) return

      const vpWidth = gameState.value.width || actualViewportWidth.value
      const vpHeight = gameState.value.height || actualViewportHeight.value

      for (const player of Object.values(gameState.value.players)) {
        const screenX = player.x
        const screenY = player.y

        if (screenX >= 0 && screenX < vpWidth && screenY >= 0 && screenY < vpHeight) {
          const color = player.color || '#ff0'
          display.draw(screenX, screenY, player.symbol, color, '#000')
        }
      }
    }

    /**
     * Render all monsters
     */
    function renderMonsters() {
      if (!gameState.value?.monsters) return

      const vpWidth = gameState.value.width || actualViewportWidth.value
      const vpHeight = gameState.value.height || actualViewportHeight.value

      for (const monster of Object.values(gameState.value.monsters)) {
        const screenX = monster.x
        const screenY = monster.y

        if (screenX >= 0 && screenX < vpWidth && screenY >= 0 && screenY < vpHeight) {
          const color = monster.color || '#f00'
          display.draw(screenX, screenY, monster.symbol, color, '#000')
        }
      }
    }

    /**
     * Full render cycle
     */
    function render() {
      if (!display || !gameState.value) return
      display.clear()
      renderMap()
      renderMonsters()
      renderPlayers()
    }

    // Watch for game state changes and re-render
    watch(gameState, (newState, oldState) => {
      if (newState && !display) {
        setupDisplay()
      }
      render()
    }, { deep: true })

    // Watch for viewport size changes
    watch([actualViewportWidth, actualViewportHeight], () => {
      if (gameState.value) {
        setupDisplay()
        render()
      }
    })

    onMounted(() => {
      if (gameState.value) {
        setupDisplay()
        render()
      }
    })

    onUnmounted(() => {
      if (display && gameCanvas.value) {
        const container = display.getContainer()
        if (container && container.parentNode) {
          container.parentNode.removeChild(container)
        }
        display = null
      }
    })

    return {
      gameCanvas
    }
  }
}
</script>

<style scoped>
.game-canvas-wrapper {
  display: inline-block;
}
</style>
