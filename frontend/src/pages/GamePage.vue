<template>
  <div class="game-page">
    <!-- Header -->
    <GameHeader />

    <!-- Room Description Overlay -->
    <RoomDescriptionOverlay />

    <!-- Map Regenerating Overlay -->
    <RegeneratingOverlay />

    <!-- Game Completed Overlay -->
    <GameCompletedOverlay />

    <!-- Combat Popup (Fight Request Confirmation) -->
    <CombatPopup
      :show="combatStore.showFightPopup"
      :monster="combatStore.pendingFightMonster"
      @accept="socketStore.acceptFight"
      @decline="socketStore.declineFight"
    />

    <!-- Combat Modal (Active Fight) -->
    <CombatModal
      :show="combatStore.showFightModal"
      :fight="combatStore.currentFight"
      :monster="combatStore.currentFightMonster"
      :players="combatStore.combatPlayers"
      :myPlayerId="playerStore.myPlayerId"
      :canJoinFight="combatStore.canJoinCurrentFight"
      :fightResult="combatStore.fightResult"
      :xpEarned="combatStore.xpEarned"
      @action="socketStore.sendCombatAction"
      @flee="socketStore.fleeFight"
      @join="socketStore.joinFight"
      @close="combatStore.closeFightResult"
    />

    <div class="main-content">
      <!-- Left Panel: Game Info & Player Stats -->
      <aside class="left-panel">
        <PlayerStatsPanel />
        <GameInfoPanel />
        <CurrentRoomPanel />
        <PlayersListPanel />
      </aside>

      <!-- Center: Game Canvas -->
      <main class="game-container">
        <GameCanvas />
      </main>

      <!-- Right Panel: Controls, Legend & Event Log -->
      <aside class="right-panel">
        <ControlsPanel />
        <LegendPanel />
        <EventLogPanel />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

// Stores
import { useSocketStore } from '../stores/socketStore'
import { useGameStore } from '../stores/gameStore'
import { usePlayerStore } from '../stores/playerStore'
import { useCombatStore } from '../stores/combatStore'
import { useEventLogStore } from '../stores/eventLogStore'

// Composables
import { useGameControls } from '../composables/useGameControls'

// Components
import GameHeader from '../components/game/GameHeader.vue'
import GameCanvas from '../components/game/GameCanvas.vue'
import RoomDescriptionOverlay from '../components/game/RoomDescriptionOverlay.vue'
import RegeneratingOverlay from '../components/game/RegeneratingOverlay.vue'
import GameCompletedOverlay from '../components/game/GameCompletedOverlay.vue'
import CombatPopup from '../components/CombatPopup.vue'
import CombatModal from '../components/CombatModal.vue'

// Panels
import PlayerStatsPanel from '../components/panels/PlayerStatsPanel.vue'
import GameInfoPanel from '../components/panels/GameInfoPanel.vue'
import CurrentRoomPanel from '../components/panels/CurrentRoomPanel.vue'
import PlayersListPanel from '../components/panels/PlayersListPanel.vue'
import ControlsPanel from '../components/panels/ControlsPanel.vue'
import LegendPanel from '../components/panels/LegendPanel.vue'
import EventLogPanel from '../components/panels/EventLogPanel.vue'

// Props
const props = defineProps({
  gameId: {
    type: String,
    required: true
  }
})

// Initialize stores
const socketStore = useSocketStore()
const gameStore = useGameStore()
const playerStore = usePlayerStore()
const combatStore = useCombatStore()
const eventLogStore = useEventLogStore()

const route = useRoute()

// Initialize keyboard controls
useGameControls()

// Lifecycle
onMounted(() => {
  eventLogStore.addLog('DungeonAI started', 'system')
  socketStore.connect(props.gameId)
})

onUnmounted(() => {
  socketStore.disconnect()
  gameStore.cleanup()
})
</script>

<style scoped>
.game-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #1a1a1a;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 0.5rem;
  padding: 0.5rem;
}

.left-panel,
.right-panel {
  background: #2c2c2c;
  border-radius: 6px;
  padding: 0.5rem;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.left-panel {
  width: 240px;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.right-panel {
  width: 220px;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.game-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #1a1a1a;
  border-radius: 6px;
  padding: 0.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: #1a1a1a;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #666;
}
</style>
