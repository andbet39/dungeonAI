import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePlayerStore = defineStore('player', () => {
  // Authentication State
  const user = ref(null)
  const userProfiles = ref([])
  const selectedProfile = ref(null)
  
  // Game State
  const myPlayerId = ref(null)
  const players = ref({})
  const displayName = ref('')
  const nickname = ref('')
  const playerStats = ref(null)

  // Player ID storage for reconnection
  const PLAYER_ID_KEY = 'dungeonai_player_id'

  /**
   * Check if user is authenticated
   */
  const isAuthenticated = computed(() => !!user.value)

  /**
   * Check if user is admin
   */
  const isAdmin = computed(() => user.value?.role === 'admin')

  /**
   * Login with email and password
   */
  async function login(email, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include'
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Login failed')
    }

    const userData = await response.json()
    user.value = userData
    
    // Fetch user's profiles
    await fetchProfiles()
  }

  /**
   * Register new user
   */
  async function register(email, password) {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include'
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Registration failed')
    }

    const userData = await response.json()
    user.value = userData
    
    // Fetch user's profiles (should be empty for new users)
    await fetchProfiles()
  }

  /**
   * Logout current user
   */
  async function logout() {
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include'
    })
    
    user.value = null
    userProfiles.value = []
    selectedProfile.value = null
    reset()
  }

  /**
   * Fetch current user info
   */
  async function fetchCurrentUser() {
    try {
      const response = await fetch('/api/auth/me', {
        credentials: 'include'
      })
      
      if (response.ok) {
        user.value = await response.json()
        await fetchProfiles()
        return true
      }
    } catch (e) {
      console.error('Error fetching user:', e)
    }
    return false
  }

  /**
   * Fetch all profiles for the current user
   */
  async function fetchProfiles() {
    try {
      const response = await fetch('/api/player/profiles', {
        credentials: 'include'
      })
      
      if (response.ok) {
        const data = await response.json()
        userProfiles.value = data.profiles
        
        // Auto-select profile if there's a selected_profile_token from cookie
        if (data.selected_profile_token) {
          const profile = data.profiles.find(p => p.token === data.selected_profile_token)
          if (profile) {
            selectedProfile.value = profile
            displayName.value = profile.display_name
            nickname.value = profile.nickname
          }
        }
        
        return data.profiles
      }
    } catch (e) {
      console.error('Error fetching profiles:', e)
    }
    return []
  }

  /**
   * Create a new player profile
   */
  async function createProfile(displayName) {
    const response = await fetch('/api/player/profiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: displayName }),
      credentials: 'include'
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to create profile')
    }

    const profile = await response.json()
    await fetchProfiles() // Refresh profile list
    await selectProfile(profile.token) // Auto-select the new profile
    return profile
  }

  /**
   * Clear selected profile (for switching profiles)
   */
  async function clearSelectedProfile() {
    // Clear the player_token cookie on backend
    try {
      await fetch('/api/player/clear-selection', {
        method: 'POST',
        credentials: 'include'
      })
    } catch (e) {
      console.error('Error clearing profile selection:', e)
    }
    
    // Clear local state
    selectedProfile.value = null
    displayName.value = ''
    nickname.value = ''
    playerStats.value = null
  }

  /**
   * Select a player profile
   */
  async function selectProfile(token) {
    const response = await fetch(`/api/player/select/${token}`, {
      method: 'POST',
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error('Failed to select profile')
    }

    const profile = userProfiles.value.find(p => p.token === token)
    if (profile) {
      selectedProfile.value = profile
      displayName.value = profile.display_name
      nickname.value = profile.nickname
      
      // Fetch full stats for this profile
      await fetchStats(token)
    }
    
    return profile
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
   * Fetch player stats for selected profile
   */
  async function fetchStats(token) {
    const profileToken = token || selectedProfile.value?.token
    if (!profileToken) return null
    
    try {
      const response = await fetch(`/api/player/${profileToken}/stats`, {
        credentials: 'include'
      })
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
   * Update display name for selected profile
   */
  async function updateDisplayName(newName) {
    if (!selectedProfile.value) return null
    
    try {
      const response = await fetch(`/api/player/${selectedProfile.value.token}/name`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: newName }),
        credentials: 'include'
      })
      if (response.ok) {
        const data = await response.json()
        setDisplayName(newName)
        await fetchProfiles() // Refresh to get updated data
        return data
      }
    } catch (e) {
      console.error('Error updating name:', e)
    }
    return null
  }

  /**
   * Generate/regenerate nickname for selected profile
   */
  async function generateNickname() {
    if (!selectedProfile.value) return null
    
    try {
      const response = await fetch(`/api/player/${selectedProfile.value.token}/nickname`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
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

  // Computed: current player token from selected profile
  const playerToken = computed(() => selectedProfile.value?.token || null)

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
    const name = displayName.value || selectedProfile.value?.display_name || 'Hero'
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

  /**
   * Get stored player ID (for reconnection)
   */
  function getStoredPlayerId() {
    return localStorage.getItem(PLAYER_ID_KEY)
  }

  return {
    // Authentication State
    user,
    userProfiles,
    selectedProfile,
    isAuthenticated,
    isAdmin,
    
    // Game State
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
    
    // Auth Actions
    login,
    register,
    logout,
    fetchCurrentUser,
    fetchProfiles,
    createProfile,
    selectProfile,
    clearSelectedProfile,
    
    // Game Actions
    getStoredPlayerId,
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
