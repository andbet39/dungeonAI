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
  background: radial-gradient(ellipse at top, #1e2749 0%, #16213e 40%, #0f1419 100%);
  position: relative;
  overflow: hidden;
}

/* Animated Background Decorations */
.game-page::before {
  content: '';
  position: absolute;
  width: 350px;
  height: 350px;
  background: #ffd700;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.06;
  top: -100px;
  left: -100px;
  animation: float 20s infinite ease-in-out;
  z-index: 0;
}

.game-page::after {
  content: '';
  position: absolute;
  width: 300px;
  height: 300px;
  background: #9b59b6;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.06;
  bottom: -100px;
  right: -100px;
  animation: float 25s infinite ease-in-out reverse;
  z-index: 0;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  33% { transform: translate(30px, -30px); }
  66% { transform: translate(-20px, 20px); }
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 0.5rem;
  padding: 0.5rem;
  position: relative;
  z-index: 1;
}

.left-panel,
.right-panel {
  background: rgba(20, 25, 40, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 12px;
  padding: 0.5rem;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.2);
  transition: all 0.3s ease;
}

.left-panel:hover,
.right-panel:hover {
  border-color: rgba(255, 215, 0, 0.35);
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
  background: rgba(15, 18, 30, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 0.5rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.2);
}

::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 215, 0, 0.05);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 215, 0, 0.3);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 215, 0, 0.5);
}
</style>
