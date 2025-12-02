import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useGameStore = defineStore('game', () => {
  // State
  const gameState = ref(null)
  const isRegenerating = ref(false)
  const currentRoom = ref(null)
  const showRoomDescription = ref(false)
  
  // Viewport dimensions (fixed size)
  const viewportWidth = ref(60)
  const viewportHeight = ref(30)

  // Room description timeout handle
  let roomDescriptionTimeout = null

  // Computed: game name
  const gameName = computed(() => {
    return gameState.value?.game_name || 'DungeonAI'
  })

  // Computed: monster count
  const monsterCount = computed(() => {
    return gameState.value?.monsters ? Object.keys(gameState.value.monsters).length : 0
  })

  // Computed: monsters as array
  const monstersList = computed(() => {
    if (!gameState.value?.monsters) return []
    return Object.values(gameState.value.monsters)
  })

  // Computed: map dimensions
  const mapWidth = computed(() => gameState.value?.map_width || 0)
  const mapHeight = computed(() => gameState.value?.map_height || 0)

  // Computed: visited rooms count
  const visitedRoomsCount = computed(() => {
    if (!gameState.value?.rooms) return 0
    return gameState.value.rooms.filter(room => room.visited).length
  })

  // Computed: total rooms count
  const totalRoomsCount = computed(() => {
    return gameState.value?.rooms?.length || 0
  })

  // Computed: game completed status
  const isGameCompleted = computed(() => {
    return gameState.value?.is_completed || false
  })

  // Computed: tiles
  const tiles = computed(() => gameState.value?.tiles || [])

  // Computed: actual viewport from server or defaults
  const actualViewportWidth = computed(() => gameState.value?.viewport_width || viewportWidth.value)
  const actualViewportHeight = computed(() => gameState.value?.viewport_height || viewportHeight.value)

  /**
   * Set the full game state from server
   */
  function setGameState(state) {
    gameState.value = state
  }

  /**
   * Set map regenerating status
   */
  function setRegenerating(value) {
    isRegenerating.value = value
  }

  /**
   * Show room description popup with auto-dismiss
   */
  function showRoomPopup(room) {
    currentRoom.value = room
    showRoomDescription.value = true

    // Clear any existing timeout
    if (roomDescriptionTimeout) {
      clearTimeout(roomDescriptionTimeout)
    }

    // Auto-dismiss after 5 seconds
    roomDescriptionTimeout = setTimeout(() => {
      showRoomDescription.value = false
    }, 5000)
  }

  /**
   * Dismiss room description popup
   */
  function dismissRoomDescription() {
    showRoomDescription.value = false
    if (roomDescriptionTimeout) {
      clearTimeout(roomDescriptionTimeout)
      roomDescriptionTimeout = null
    }
  }

  /**
   * Set current room without showing popup
   */
  function setCurrentRoom(room) {
    currentRoom.value = room
  }

  /**
   * Reset game state
   */
  function reset() {
    gameState.value = null
    isRegenerating.value = false
    currentRoom.value = null
    showRoomDescription.value = false
    if (roomDescriptionTimeout) {
      clearTimeout(roomDescriptionTimeout)
      roomDescriptionTimeout = null
    }
  }

  /**
   * Cleanup on unmount
   */
  function cleanup() {
    if (roomDescriptionTimeout) {
      clearTimeout(roomDescriptionTimeout)
      roomDescriptionTimeout = null
    }
  }

  return {
    // State
    gameState,
    isRegenerating,
    currentRoom,
    showRoomDescription,
    viewportWidth,
    viewportHeight,

    // Getters
    gameName,
    monsterCount,
    monstersList,
    mapWidth,
    mapHeight,
    visitedRoomsCount,
    totalRoomsCount,
    isGameCompleted,
    tiles,
    actualViewportWidth,
    actualViewportHeight,

    // Actions
    setGameState,
    setRegenerating,
    showRoomPopup,
    dismissRoomDescription,
    setCurrentRoom,
    reset,
    cleanup
  }
})
