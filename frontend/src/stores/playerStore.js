import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  // State
  const myPlayerId = ref(null)
  const players = ref({})
  const displayName = ref('')
  const nickname = ref('')
  const playerStats = ref(null)

  // Player token management (persisted in localStorage)
  const PLAYER_TOKEN_KEY = 'dungeonai_player_token'
  const PLAYER_ID_KEY = 'dungeonai_player_id'
  const PLAYER_NAME_KEY = 'dungeonai_display_name'

  /**
   * Get or create player token from localStorage
   */
  function getPlayerToken() {
    let token = localStorage.getItem(PLAYER_TOKEN_KEY)
    if (!token) {
      token = crypto.randomUUID()
      localStorage.setItem(PLAYER_TOKEN_KEY, token)
    }
    return token
  }

  /**
   * Get stored player ID (for reconnection)
   */
  function getStoredPlayerId() {
    return localStorage.getItem(PLAYER_ID_KEY)
  }

  /**
   * Set the current player ID
   */
  function setMyPlayerId(playerId) {
    myPlayerId.value = playerId
    if (playerId) {
      localStorage.setItem(PLAYER_ID_KEY, playerId)
    }
  }

  /**
   * Update the players object
   */
  function setPlayers(newPlayers) {
    players.value = newPlayers || {}
  }

  /**
   * Set display name locally and in storage
   */
  function setDisplayName(name) {
    displayName.value = name
    if (name) {
      localStorage.setItem(PLAYER_NAME_KEY, name)
    }
  }

  /**
   * Set nickname
   */
  function setNickname(newNickname) {
    nickname.value = newNickname
  }

  /**
   * Set player stats
   */
  function setPlayerStats(stats) {
    playerStats.value = stats
    if (stats?.display_name) {
      displayName.value = stats.display_name
    }
    if (stats?.nickname) {
      nickname.value = stats.nickname
    }
  }

  /**
   * Fetch player stats from server
   */
  async function fetchStats() {
    const token = getPlayerToken()
    try {
      const response = await fetch(`/api/player/${token}/stats`)
      if (response.ok) {
        const stats = await response.json()
        setPlayerStats(stats)
        return stats
      }
    } catch (e) {
      console.error('Error fetching stats:', e)
    }
    return null
  }

  /**
   * Update display name on server
   */
  async function updateDisplayName(newName) {
    const token = getPlayerToken()
    try {
      const response = await fetch(`/api/player/${token}/name`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: newName })
      })
      if (response.ok) {
        const data = await response.json()
        setDisplayName(newName)
        return data
      }
    } catch (e) {
      console.error('Error updating name:', e)
    }
    return null
  }

  /**
   * Generate/regenerate nickname
   */
  async function generateNickname() {
    const token = getPlayerToken()
    try {
      const response = await fetch(`/api/player/${token}/nickname`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      if (response.ok) {
        const data = await response.json()
        setNickname(data.nickname)
        return data
      }
    } catch (e) {
      console.error('Error generating nickname:', e)
    }
    return null
  }

  /**
   * Get stored display name from localStorage
   */
  function getStoredDisplayName() {
    return localStorage.getItem(PLAYER_NAME_KEY)
  }

  // Computed: current player token
  const playerToken = computed(() => getPlayerToken())

  // Computed: current player object with world coordinates
  const myPlayer = computed(() => {
    if (!players.value || !myPlayerId.value) return null
    const player = players.value[myPlayerId.value]
    if (!player) return null
    return {
      ...player,
      x: player.world_x !== undefined ? player.world_x : player.x,
      y: player.world_y !== undefined ? player.world_y : player.y
    }
  })

  // Computed: full title (name + nickname)
  const fullTitle = computed(() => {
    const name = displayName.value || `Hero_${getPlayerToken().substring(0, 6)}`
    if (nickname.value) {
      return `${name} ${nickname.value}`
    }
    return name
  })

  // Computed: players as array
  const playersList = computed(() => {
    return Object.values(players.value)
  })

  // Computed: player count
  const playerCount = computed(() => {
    return Object.keys(players.value).length
  })

  // Computed: HP percentage for current player
  const hpPercentage = computed(() => {
    if (!myPlayer.value) return 100
    return Math.round((myPlayer.value.hp / myPlayer.value.max_hp) * 100)
  })

  // Computed: HP bar CSS class
  const hpBarClass = computed(() => {
    const pct = hpPercentage.value
    if (pct > 60) return 'hp-high'
    if (pct > 30) return 'hp-medium'
    return 'hp-low'
  })

  /**
   * Format ability modifier for display
   */
  function formatMod(mod) {
    if (mod === undefined || mod === null) return '+0'
    return mod >= 0 ? `+${mod}` : `${mod}`
  }

  /**
   * Reset player state
   */
  function reset() {
    myPlayerId.value = null
    players.value = {}
    playerStats.value = null
  }

  return {
    // State
    myPlayerId,
    players,
    displayName,
    nickname,
    playerStats,
    
    // Getters
    myPlayer,
    playerToken,
    fullTitle,
    playersList,
    playerCount,
    hpPercentage,
    hpBarClass,
    
    // Actions
    getPlayerToken,
    getStoredPlayerId,
    getStoredDisplayName,
    setMyPlayerId,
    setPlayers,
    setDisplayName,
    setNickname,
    setPlayerStats,
    fetchStats,
    updateDisplayName,
    generateNickname,
    formatMod,
    reset
  }
})
