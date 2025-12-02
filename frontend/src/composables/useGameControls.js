import { onMounted, onUnmounted } from 'vue'
import { useSocketStore } from '../stores/socketStore'
import { useCombatStore } from '../stores/combatStore'
import { useGameStore } from '../stores/gameStore'
import { usePlayerStore } from '../stores/playerStore'

/**
 * Movement key mappings
 * Maps keyboard keys to [dx, dy] movement vectors
 */
const KEY_MAP = {
  // Arrow keys
  'ArrowUp': [0, -1],
  'ArrowDown': [0, 1],
  'ArrowLeft': [-1, 0],
  'ArrowRight': [1, 0],
  // Vim keys
  'k': [0, -1],
  'j': [0, 1],
  'h': [-1, 0],
  'l': [1, 0],
  // Numpad
  '8': [0, -1],
  '2': [0, 1],
  '4': [-1, 0],
  '6': [1, 0]
}

/**
 * Action keys for interaction
 */
const ACTION_KEYS = [' ', 'e', 'Enter']

/**
 * Composable for handling game keyboard controls
 * Automatically registers/unregisters event listeners on mount/unmount
 */
export function useGameControls() {
  const socketStore = useSocketStore()
  const combatStore = useCombatStore()
  const gameStore = useGameStore()
  const playerStore = usePlayerStore()

  /**
   * Handle keydown events for game controls
   */
  function handleKeyDown(e) {
    // Don't handle if not connected or no player
    if (!playerStore.myPlayerId || !gameStore.gameState) return

    // Block input during combat UI
    if (combatStore.isCombatActive) {
      return
    }

    // Dismiss room description on any key
    if (gameStore.showRoomDescription) {
      gameStore.dismissRoomDescription()
    }

    // Handle movement
    const direction = KEY_MAP[e.key]
    if (direction) {
      e.preventDefault()
      socketStore.sendMove(direction[0], direction[1])
      return
    }

    // Handle interaction
    if (ACTION_KEYS.includes(e.key)) {
      e.preventDefault()
      socketStore.sendInteract()
      return
    }
  }

  /**
   * Start listening for keyboard events
   */
  function startListening() {
    window.addEventListener('keydown', handleKeyDown)
  }

  /**
   * Stop listening for keyboard events
   */
  function stopListening() {
    window.removeEventListener('keydown', handleKeyDown)
  }

  // Auto-register on mount, unregister on unmount
  onMounted(() => {
    startListening()
  })

  onUnmounted(() => {
    stopListening()
  })

  return {
    startListening,
    stopListening
  }
}
