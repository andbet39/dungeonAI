import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from './gameStore'
import { usePlayerStore } from './playerStore'
import { useCombatStore } from './combatStore'
import { useEventLogStore } from './eventLogStore'

export const useSocketStore = defineStore('socket', () => {
  // State
  const isConnected = ref(false)
  const currentGameId = ref(null)

  // Private socket instance
  let socket = null
  let reconnectTimeout = null
  let router = null

  /**
   * Initialize router for navigation on errors
   */
  function initRouter(routerInstance) {
    router = routerInstance
  }

  /**
   * Connect to WebSocket for a specific game
   */
  function connect(gameId) {
    // Cleanup any existing connection
    disconnect()

    currentGameId.value = gameId
    const playerStore = usePlayerStore()
    const eventLogStore = useEventLogStore()

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // Cookies (access_token and player_token) are automatically sent with WebSocket connection
    const wsUrl = `${protocol}//${window.location.host}/ws?game_id=${gameId}`

    socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      isConnected.value = true
      eventLogStore.addLog('Connected to server', 'system')

      // Send initial handshake with stored player_id for reconnection
      const storedPlayerId = playerStore.getStoredPlayerId()
      send({ type: 'reconnect', player_id: storedPlayerId })
    }

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data)
      handleMessage(message)
    }

    socket.onclose = (event) => {
      isConnected.value = false

      // Check if it was an error close (game not found, etc)
      if (event.code === 4404) {
        eventLogStore.addLog('Game not found. Returning to lobby...', 'error')
        if (router) {
          setTimeout(() => router.push({ name: 'lobby' }), 2000)
        }
        return
      }

      eventLogStore.addLog('Disconnected from server. Reconnecting...', 'error')

      // Auto-reconnect after 2 seconds
      reconnectTimeout = setTimeout(() => {
        if (currentGameId.value) {
          connect(currentGameId.value)
        }
      }, 2000)
    }

    socket.onerror = (error) => {
      eventLogStore.addLog('WebSocket error occurred', 'error')
      console.error('WebSocket error:', error)
    }
  }

  /**
   * Disconnect from WebSocket
   */
  function disconnect() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }

    if (socket) {
      socket.close()
      socket = null
    }

    isConnected.value = false
    currentGameId.value = null
  }

  /**
   * Send a message through WebSocket
   */
  function send(message) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message))
      return true
    }
    return false
  }

  // ==================== Game Actions ====================

  /**
   * Send move command
   */
  function sendMove(dx, dy) {
    return send({ type: 'move', dx, dy })
  }

  /**
   * Send interact command
   */
  function sendInteract() {
    const eventLogStore = useEventLogStore()
    if (send({ type: 'interact' })) {
      eventLogStore.addLog('Interacting with nearby objects...', 'action')
      return true
    }
    return false
  }

  // ==================== Combat Actions ====================

  /**
   * Accept a fight (either new fight or join existing)
   */
  function acceptFight() {
    const combatStore = useCombatStore()
    const eventLogStore = useEventLogStore()

    const joinFightId = combatStore.getPendingJoinFightId()
    const monsterId = combatStore.getPendingFightMonsterId()

    if (joinFightId) {
      send({ type: 'join_fight', fight_id: joinFightId })
      eventLogStore.addLog('Joining the fight!', 'combat')
      combatStore.clearPendingJoinFightId()
    } else if (monsterId) {
      send({ type: 'request_fight', monster_id: monsterId })
      eventLogStore.addLog('Engaging in combat!', 'combat')
    }

    combatStore.clearPendingFight()
  }

  /**
   * Decline a fight
   */
  function declineFight() {
    const combatStore = useCombatStore()
    const eventLogStore = useEventLogStore()

    send({ type: 'decline_fight' })
    combatStore.clearPendingFight()
    eventLogStore.addLog('Retreated from combat', 'action')
  }

  /**
   * Join an ongoing fight
   */
  function joinFight() {
    const combatStore = useCombatStore()
    const eventLogStore = useEventLogStore()

    if (combatStore.currentFight) {
      send({ type: 'join_fight', fight_id: combatStore.currentFight.id })
      eventLogStore.addLog('Joining the fight!', 'combat')
      combatStore.clearPendingJoinFightId()
    }
  }

  /**
   * Flee from current fight
   */
  function fleeFight() {
    const combatStore = useCombatStore()
    const eventLogStore = useEventLogStore()

    if (combatStore.currentFight) {
      send({ type: 'flee_fight', fight_id: combatStore.currentFight.id })
      eventLogStore.addLog('Fleeing from combat!', 'action')
    }
  }

  /**
   * Send a combat action
   */
  function sendCombatAction(action) {
    const combatStore = useCombatStore()
    const eventLogStore = useEventLogStore()

    if (combatStore.currentFight) {
      send({ type: 'combat_action', fight_id: combatStore.currentFight.id, action: action })
      eventLogStore.addLog(`Used ${action}!`, 'combat')
    }
  }

  // ==================== Message Handlers ====================

  /**
   * Handle incoming WebSocket messages
   */
  function handleMessage(message) {
    const gameStore = useGameStore()
    const playerStore = usePlayerStore()
    const combatStore = useCombatStore()
    const eventLogStore = useEventLogStore()

    switch (message.type) {
      case 'welcome':
        playerStore.setMyPlayerId(message.playerId)
        gameStore.setGameState(message.state)
        if (message.state?.players) {
          playerStore.setPlayers(message.state.players)
        }
        if (message.isReconnection) {
          eventLogStore.addLog(`Welcome back! Reconnected as Player ${message.playerId.substring(0, 4)}`, 'success')
        } else {
          eventLogStore.addLog(`Welcome! You are Player ${message.playerId.substring(0, 4)}`, 'success')
        }
        break

      case 'state_update':
        gameStore.setGameState(message.state)
        if (message.state?.players) {
          playerStore.setPlayers(message.state.players)
        }
        break

      case 'player_joined':
        eventLogStore.addLog(`Player ${message.playerId.substring(0, 4)} joined the game`, 'join')
        break

      case 'player_left':
        eventLogStore.addLog(`Player ${message.playerId.substring(0, 4)} left the game`, 'leave')
        break

      case 'room_entered':
        if (message.room) {
          gameStore.showRoomPopup(message.room)
          eventLogStore.addLog(`Entered: ${message.room.name}`, 'room')
        }
        break

      case 'map_regenerating':
        gameStore.setRegenerating(true)
        eventLogStore.addLog('Map is being regenerated...', 'system')
        break

      case 'map_regenerated':
        gameStore.setRegenerating(false)
        gameStore.setGameState(message.state)
        if (message.state?.players) {
          playerStore.setPlayers(message.state.players)
        }
        eventLogStore.addLog('New dungeon generated!', 'success')
        break

      case 'pong':
        // Heartbeat response, no action needed
        break

      case 'fight_request':
        combatStore.handleFightRequest(message.monster, message.monster_id)
        eventLogStore.addLog(`Encountered a ${message.monster.name}!`, 'combat')
        break

      case 'can_join_fight':
        combatStore.handleCanJoinFight(message.fight, message.monster, message.fight_id)
        eventLogStore.addLog(`A fight with ${message.monster.name} is happening nearby!`, 'combat')
        break

      case 'fight_started':
        // Build players in fight from gameState
        let playersInFight = {}
        if (message.fight?.player_ids && gameStore.gameState?.players) {
          for (const pid of message.fight.player_ids) {
            if (gameStore.gameState.players[pid]) {
              playersInFight[pid] = { ...gameStore.gameState.players[pid] }
            }
          }
        }
        combatStore.handleFightStarted(message.fight, message.monster, playersInFight)
        eventLogStore.addLog(`Combat started with ${message.monster.name}!`, 'combat')
        break

      case 'fight_updated':
        combatStore.handleFightUpdated(message.fight, message.monster, message.players)
        break

      case 'player_fled':
        eventLogStore.addLog('A player has fled from combat!', 'leave')
        break

      case 'fight_left':
        combatStore.handleFightLeft()
        eventLogStore.addLog('You escaped from combat!', 'success')
        break

      case 'fight_ended':
        combatStore.handleFightEnded(message.result, message.fight, message.xp_earned || 0, message.monster_type)
        eventLogStore.addLog(`Combat ended: ${message.result}`, 'system')
        break

      case 'monster_attacks':
        combatStore.handleMonsterAttacks(message.fight, message.monster, message.players)
        eventLogStore.addLog(`${message.monster.name} attacks you!`, 'combat')
        break

      case 'player_respawned':
        eventLogStore.addLog('You have been resurrected! HP restored to full.', 'success')
        break

      case 'fight_declined':
        // No action needed
        break

      case 'error':
        eventLogStore.addLog(message.message || 'An error occurred', 'error')
        // Handle fight-related errors
        if (message.message && (
          message.message.includes('Already in fight') ||
          message.message.includes('Fight not found') ||
          message.message.includes('Not in fight') ||
          message.message.includes('Not in this fight')
        )) {
          combatStore.handleFightError()
        }
        break

      default:
        console.log('Unknown message type:', message.type)
    }
  }

  /**
   * Cleanup on unmount
   */
  function cleanup() {
    disconnect()
  }

  return {
    // State
    isConnected,
    currentGameId,

    // Connection
    initRouter,
    connect,
    disconnect,
    send,
    cleanup,

    // Game actions
    sendMove,
    sendInteract,

    // Combat actions
    acceptFight,
    declineFight,
    joinFight,
    fleeFight,
    sendCombatAction
  }
})
