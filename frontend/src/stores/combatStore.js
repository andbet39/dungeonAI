import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { usePlayerStore } from './playerStore'

export const useCombatStore = defineStore('combat', () => {
  // State
  const showFightPopup = ref(false)
  const showFightModal = ref(false)
  const pendingFightMonster = ref(null)
  const pendingFightMonsterId = ref(null)
  const currentFight = ref(null)
  const currentFightMonster = ref(null)
  const pendingJoinFightId = ref(null)
  const fightResult = ref(null)
  const combatPlayers = ref({})
  const xpEarned = ref(0)
  const killedMonsterType = ref(null)
  // Computed: can join the current fight
  const canJoinCurrentFight = computed(() => {
    const playerStore = usePlayerStore()
    if (!currentFight.value || !playerStore.myPlayerId) return false
    if (currentFight.value.player_ids?.includes(playerStore.myPlayerId)) return false
    return pendingJoinFightId.value === currentFight.value.id
  })

  // Computed: is player currently in a fight
  const isInFight = computed(() => {
    const playerStore = usePlayerStore()
    return showFightModal.value && currentFight.value?.player_ids?.includes(playerStore.myPlayerId)
  })

  // Computed: check if any combat UI is showing (for blocking input)
  const isCombatActive = computed(() => {
    return showFightModal.value || showFightPopup.value
  })

  /**
   * Handle fight request from server
   */
  function handleFightRequest(monster, monsterId) {
    pendingFightMonster.value = monster
    pendingFightMonsterId.value = monsterId
    showFightPopup.value = true
    fightResult.value = null
  }

  /**
   * Handle can join fight notification
   */
  function handleCanJoinFight(fight, monster, fightId) {
    currentFight.value = fight
    currentFightMonster.value = monster
    pendingFightMonster.value = monster
    pendingJoinFightId.value = fightId
    showFightPopup.value = true
    fightResult.value = null
  }

  /**
   * Handle fight started
   */
  function handleFightStarted(fight, monster, playersInFight) {
    currentFight.value = fight
    currentFightMonster.value = monster
    showFightPopup.value = false
    showFightModal.value = true
    fightResult.value = null
    pendingFightMonster.value = null
    pendingFightMonsterId.value = null

    // Initialize combatPlayers
    if (playersInFight) {
      combatPlayers.value = { ...playersInFight }
    }
  }

  /**
   * Handle fight updated
   */
  function handleFightUpdated(fight, monster, players) {
    if (!fightResult.value) {
      currentFight.value = fight
      currentFightMonster.value = monster
      if (players) {
        combatPlayers.value = { ...players }
      }
    }
  }

  /**
   * Handle monster attacks
   */
  function handleMonsterAttacks(fight, monster, players) {
    currentFight.value = fight
    currentFightMonster.value = monster
    showFightModal.value = true
    fightResult.value = null
    if (players) {
      combatPlayers.value = { ...players }
    }
  }

  /**
   * Handle fight left (player fled)
   */
  function handleFightLeft() {
    showFightModal.value = false
    currentFight.value = null
    currentFightMonster.value = null
  }

  /**
   * Handle fight ended
   */
  function handleFightEnded(result, fight, xp = 0, monsterType = null) {
    fightResult.value = result
    xpEarned.value = xp
    killedMonsterType.value = monsterType
    if (fight) {
      currentFight.value = fight
    }
  }

  /**
   * Close fight result and reset modal
   */
  function closeFightResult() {
    showFightModal.value = false
    currentFight.value = null
    currentFightMonster.value = null
    fightResult.value = null
    xpEarned.value = 0
    killedMonsterType.value = null
  }

  /**
   * Clear pending fight (on decline)
   */
  function clearPendingFight() {
    showFightPopup.value = false
    pendingFightMonster.value = null
    pendingFightMonsterId.value = null
    pendingJoinFightId.value = null
  }

  /**
   * Get pending fight monster ID for accepting fight
   */
  function getPendingFightMonsterId() {
    return pendingFightMonsterId.value
  }

  /**
   * Get pending join fight ID
   */
  function getPendingJoinFightId() {
    return pendingJoinFightId.value
  }

  /**
   * Clear pending join fight ID after accepting
   */
  function clearPendingJoinFightId() {
    pendingJoinFightId.value = null
  }

  /**
   * Handle fight-related error - cleanup stuck state
   */
  function handleFightError() {
    showFightModal.value = false
    currentFight.value = null
    currentFightMonster.value = null
    showFightPopup.value = false
    pendingFightMonster.value = null
    pendingFightMonsterId.value = null
    pendingJoinFightId.value = null
  }

  /**
   * Reset combat state
   */
  function reset() {
    showFightPopup.value = false
    showFightModal.value = false
    pendingFightMonster.value = null
    pendingFightMonsterId.value = null
    currentFight.value = null
    currentFightMonster.value = null
    pendingJoinFightId.value = null
    fightResult.value = null
    combatPlayers.value = {}
    xpEarned.value = 0
    killedMonsterType.value = null
  }

  return {
    // State
    showFightPopup,
    showFightModal,
    pendingFightMonster,
    currentFight,
    currentFightMonster,
    fightResult,
    combatPlayers,
    xpEarned,
    killedMonsterType,

    // Getters
    canJoinCurrentFight,
    isInFight,
    isCombatActive,

    // Actions
    handleFightRequest,
    handleCanJoinFight,
    handleFightStarted,
    handleFightUpdated,
    handleMonsterAttacks,
    handleFightLeft,
    handleFightEnded,
    closeFightResult,
    clearPendingFight,
    getPendingFightMonsterId,
    getPendingJoinFightId,
    clearPendingJoinFightId,
    handleFightError,
    reset
  }
})
