<template>
  <transition name="modal-fade">
    <div class="combat-modal-overlay" v-if="show && (fightResult || (fight && monster))">
      <div class="combat-modal">
        <!-- Header with timer -->
        <div class="combat-header">
          <div class="fight-title">
            <span class="fight-icon">⚔️</span>
            <h2>COMBAT</h2>
          </div>
          <div class="turn-timer" :class="{ warning: timerWarning, critical: timerCritical }" v-if="!fightResult">
            <span class="timer-label">Turn Timer:</span>
            <span class="timer-value">{{ formattedTime }}</span>
          </div>
        </div>

        <!-- Main combat area - stays visible until showResult is true -->
        <div class="combat-body" v-if="!showResult">
          <!-- Left Panel: Players -->
          <div class="combat-panel players-panel">
            <h3>⚔️ Heroes</h3>
            <div class="combatants-list">
              <div 
                v-for="player in fightPlayers" 
                :key="player.id"
                class="combatant-card"
                :class="{ 
                  'is-current-turn': fight?.current_turn_id === player.id,
                  'is-you': player.id === myPlayerId 
                }"
              >
                <div class="combatant-symbol" :style="{ color: player.color }">
                  {{ player.symbol }}
                </div>
                <div class="combatant-info">
                  <div class="combatant-name">
                    {{ player.id === myPlayerId ? 'You' : `Player ${player.id.substring(0, 4)}` }}
                  </div>
                  <div class="hp-bar-container">
                    <div class="hp-bar" :style="{ width: getHpPercent(player) + '%' }"></div>
                    <span class="hp-text">{{ player.hp }}/{{ player.max_hp }}</span>
                  </div>
                </div>
                <div class="turn-indicator" v-if="fight?.current_turn_id === player.id">
                  ◆
                </div>
              </div>
            </div>
            
            <!-- Join Fight Button -->
            <button 
              v-if="canJoinFight" 
              class="btn-join-fight"
              @click="$emit('join')"
            >
              🤝 Join Fight
            </button>
          </div>

          <!-- Center Panel: Combat Log & Turn Info -->
          <div class="combat-panel center-panel">
            <div class="turn-indicator-large">
              <template v-if="isMyTurn">
                <span class="your-turn">⚡ YOUR TURN ⚡</span>
              </template>
              <template v-else-if="fight?.is_monster_turn">
                <span class="monster-turn">🐲 Monster's Turn</span>
              </template>
              <template v-else>
                <span class="waiting">Waiting for {{ currentTurnPlayerName }}...</span>
              </template>
            </div>
            
            <div class="combat-log" ref="combatLogRef">
              <div 
                v-for="(entry, index) in combatLog" 
                :key="index"
                class="log-entry"
                :class="entry.type"
              >
                {{ entry.message }}
              </div>
              <!-- Dice Rolling Animation in Log -->
              <div v-if="isRollingDice" class="log-entry rolling">
                🎲 Rolling... [ {{ rollingNumbers }} ]
              </div>
              <div v-if="combatLog.length === 0 && !isRollingDice" class="log-empty">
                Combat begins...
              </div>
            </div>
          </div>

          <!-- Right Panel: Monster -->
          <div class="combat-panel monster-panel">
            <h3>🐲 Enemy</h3>
            <div 
              class="combatant-card monster-card"
              :class="{ 'is-current-turn': fight?.is_monster_turn }"
            >
              <div class="monster-symbol-large" :style="{ color: monster?.color }">
                {{ monster?.symbol }}
              </div>
              <div class="monster-name">{{ monster?.name }}</div>
              
              <!-- Large HP Display -->
              <div class="monster-hp-display">
                <span class="hp-icon">❤️</span>
                <span class="hp-current" :class="{ 'hp-low': getMonsterHpPercent() < 30, 'hp-critical': getMonsterHpPercent() < 15 }">
                  {{ monster?.stats?.hp }}
                </span>
                <span class="hp-separator">/</span>
                <span class="hp-max">{{ monster?.stats?.max_hp }}</span>
              </div>
              
              <div class="hp-bar-container monster-hp">
                <div 
                  class="hp-bar" 
                  :style="{ width: getMonsterHpPercent() + '%' }"
                  :class="{ 'hp-bar-low': getMonsterHpPercent() < 30, 'hp-bar-critical': getMonsterHpPercent() < 15 }"
                ></div>
              </div>
              <div class="turn-indicator" v-if="fight?.is_monster_turn">
                ◆
              </div>
            </div>
            
            <div class="monster-stats-compact">
              <div class="stat-row">
                <span class="stat-name">AC</span>
                <span class="stat-val">{{ monster?.stats?.ac }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-name">Speed</span>
                <span class="stat-val">{{ monster?.stats?.speed }}ft</span>
              </div>
            </div>
            
            <div class="monster-abilities">
              <div class="ability-row" v-for="ability in monsterAbilities" :key="ability.name">
                <span class="ability-name">{{ ability.name }}</span>
                <span class="ability-mod" :class="{ positive: ability.modifier >= 0 }">
                  {{ ability.modifier >= 0 ? '+' : '' }}{{ ability.modifier }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer: Action buttons -->
        <div class="combat-footer" v-if="!fightResult">
          <div class="action-buttons">
            <button 
              class="action-btn attack"
              :disabled="!isMyTurn || isRollingDice"
              @click="handleAction('attack')"
            >
              ⚔️ Attack
            </button>
            <button 
              class="action-btn defend"
              :disabled="!isMyTurn || isRollingDice"
              @click="handleAction('defend')"
            >
              🛡️ Defend
            </button>
            <button 
              class="action-btn item"
              :disabled="!isMyTurn || isRollingDice"
              @click="handleAction('item')"
            >
              🧪 Use Item
            </button>
            <button 
              class="action-btn flee"
              :disabled="!isMyTurn || isRollingDice"
              @click="handleAction('flee')"
            >
              🏃 Flee
            </button>
          </div>
          <div class="action-hint" v-if="!isMyTurn">
            Wait for your turn to take an action
          </div>
        </div>

        <!-- Victory/Defeat Result Screen -->
        <div class="fight-result-overlay" v-if="showResult">
          <div class="fight-result-content" :class="fightResult">
            <div class="result-icon">{{ fightResult === 'victory' ? '🏆' : '💀' }}</div>
            <h2 class="result-title">{{ fightResult === 'victory' ? 'VICTORY!' : 'DEFEAT' }}</h2>
            <p class="result-message" v-if="fightResult === 'victory'">
              You have slain the {{ monster?.name }}!
            </p>
            <p class="result-message" v-else>
              You have been defeated...
            </p>
            <div class="result-rewards" v-if="fightResult === 'victory'">
              <div class="reward-item">✨ +{{ xpEarned }} XP earned!</div>
            </div>
            <button class="btn-continue" @click="$emit('close')">
              {{ fightResult === 'victory' ? '🎮 Continue Adventure' : '💔 Return to Game' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

export default {
  name: 'CombatModal',
  props: {
    show: {
      type: Boolean,
      default: false
    },
    fight: {
      type: Object,
      default: null
    },
    monster: {
      type: Object,
      default: null
    },
    players: {
      type: Object, // All game players
      default: () => ({})
    },
    myPlayerId: {
      type: String,
      default: ''
    },
    canJoinFight: {
      type: Boolean,
      default: false
    },
    fightResult: {
      type: String,
      default: null // 'victory' or 'defeat'
    },
    xpEarned: {
      type: Number,
      default: 0
    }
  },
  emits: ['action', 'flee', 'join', 'close'],
  setup(props, { emit }) {
    const combatLogRef = ref(null)
    const currentTime = ref(Date.now())
    let timerInterval = null
    
    // Delayed fight result display
    const showResult = ref(false)
    let resultTimeout = null
    
    // Dice rolling animation state
    const isRollingDice = ref(false)
    const rollingNumbers = ref('--')
    let diceAnimationInterval = null
    
    // Function to trigger dice roll animation
    const rollDice = (action, callback) => {
      isRollingDice.value = true
      
      // Animate random numbers
      diceAnimationInterval = setInterval(() => {
        const num1 = Math.floor(Math.random() * 20) + 1
        const num2 = Math.floor(Math.random() * 6) + 1
        rollingNumbers.value = action === 'attack' ? `${num1}, ${num2}` : `${num1}`
      }, 50)
      
      // Random duration between 800ms and 2000ms for suspense
      const duration = 800 + Math.random() * 1200
      
      setTimeout(() => {
        clearInterval(diceAnimationInterval)
        isRollingDice.value = false
        // Scroll to bottom after animation
        if (combatLogRef.value) {
          combatLogRef.value.scrollTop = combatLogRef.value.scrollHeight
        }
        if (callback) callback()
      }, duration)
    }
    
    // Wrapped action handler with dice animation
    const handleAction = (action) => {
      if (action === 'flee') {
        emit('flee')
        return
      }
      rollDice(action, () => {
        emit('action', action)
      })
    }
    
    // Update current time every 100ms for smooth timer
    onMounted(() => {
      timerInterval = setInterval(() => {
        currentTime.value = Date.now()
      }, 100)
    })
    
    onUnmounted(() => {
      if (timerInterval) {
        clearInterval(timerInterval)
      }
    })
    
    // Computed: Time remaining in current turn
    const timeRemaining = computed(() => {
      if (!props.fight?.turn_end_time) return 0
      const remaining = (props.fight.turn_end_time * 1000) - currentTime.value
      return Math.max(0, remaining / 1000)
    })
    
    const formattedTime = computed(() => {
      const total = Math.ceil(timeRemaining.value)
      const minutes = Math.floor(total / 60)
      const seconds = total % 60
      return `${minutes}:${seconds.toString().padStart(2, '0')}`
    })
    
    const timerWarning = computed(() => {
      return timeRemaining.value <= 30 && timeRemaining.value > 10
    })
    
    const timerCritical = computed(() => {
      return timeRemaining.value <= 10
    })
    
    // Get players in this fight
    const fightPlayers = computed(() => {
      if (!props.fight?.player_ids || !props.players) return []
      return props.fight.player_ids
        .map(id => props.players[id])
        .filter(p => p)
    })
    
    // Check if it's my turn
    const isMyTurn = computed(() => {
      return props.fight?.current_turn_id === props.myPlayerId
    })
    
    // Get name of current turn player
    const currentTurnPlayerName = computed(() => {
      if (!props.fight) return ''
      const currentId = props.fight.current_turn_id
      if (currentId === props.fight.monster_id) return props.monster?.name || 'Monster'
      if (currentId === props.myPlayerId) return 'You'
      return `Player ${currentId?.substring(0, 4)}`
    })
    
    // Combat log entries
    const combatLog = computed(() => {
      return props.fight?.combat_log || []
    })
    
    // Monster abilities with modifiers
    const monsterAbilities = computed(() => {
      const stats = props.monster?.stats || {}
      const getModifier = (val) => Math.floor((val - 10) / 2)
      return [
        { name: 'STR', modifier: getModifier(stats.str || 10) },
        { name: 'DEX', modifier: getModifier(stats.dex || 10) },
        { name: 'CON', modifier: getModifier(stats.con || 10) },
        { name: 'INT', modifier: getModifier(stats.int || 10) },
        { name: 'WIS', modifier: getModifier(stats.wis || 10) },
        { name: 'CHA', modifier: getModifier(stats.cha || 10) }
      ]
    })
    
    // HP percentage calculations
    const getHpPercent = (player) => {
      if (!player || !player.max_hp) return 100
      return Math.max(0, Math.min(100, (player.hp / player.max_hp) * 100))
    }
    
    const getMonsterHpPercent = () => {
      if (!props.monster?.stats) return 100
      const { hp, max_hp } = props.monster.stats
      if (!max_hp) return 100
      return Math.max(0, Math.min(100, (hp / max_hp) * 100))
    }
    
    // Auto-scroll combat log
    watch(() => props.fight?.combat_log?.length, async () => {
      await nextTick()
      if (combatLogRef.value) {
        combatLogRef.value.scrollTop = combatLogRef.value.scrollHeight
      }
    })
    
    // Delay showing fight result to allow viewing last action
    watch(() => props.fightResult, (newResult) => {
      if (resultTimeout) {
        clearTimeout(resultTimeout)
        resultTimeout = null
      }
      
      if (newResult) {
        // Show result after 1.5 second delay
        resultTimeout = setTimeout(() => {
          showResult.value = true
        }, 1500)
      } else {
        showResult.value = false
      }
    })
    
    // Cleanup result timeout on unmount
    onUnmounted(() => {
      if (resultTimeout) {
        clearTimeout(resultTimeout)
      }
    })
    
    return {
      combatLogRef,
      timeRemaining,
      formattedTime,
      timerWarning,
      timerCritical,
      fightPlayers,
      isMyTurn,
      currentTurnPlayerName,
      combatLog,
      monsterAbilities,
      getHpPercent,
      getMonsterHpPercent,
      // Dice rolling
      isRollingDice,
      rollingNumbers,
      handleAction,
      // Delayed result
      showResult
    }
  }
}
</script>

<style scoped>
.combat-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.combat-modal {
  background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
  border: 2px solid #8b0000;
  border-radius: 16px;
  width: 90%;
  max-width: 1000px;
  height: 550px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 0 50px rgba(139, 0, 0, 0.5), inset 0 0 30px rgba(0, 0, 0, 0.5);
  animation: modalAppear 0.4s ease-out;
  position: relative;
  overflow: hidden;
}

@keyframes modalAppear {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Header */
.combat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #333;
  background: rgba(139, 0, 0, 0.2);
}

.fight-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fight-icon {
  font-size: 1.5rem;
}

.fight-title h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #ff4444;
  text-transform: uppercase;
  letter-spacing: 3px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
}

.turn-timer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 8px;
  border: 1px solid #333;
}

.timer-label {
  color: #888;
  font-size: 0.85rem;
}

.timer-value {
  font-size: 1.5rem;
  font-weight: bold;
  font-family: monospace;
  color: #2ecc71;
}

.turn-timer.warning .timer-value {
  color: #f39c12;
}

.turn-timer.critical .timer-value {
  color: #e74c3c;
  animation: pulse 0.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Body */
.combat-body {
  display: flex;
  flex: 1;
  min-height: 0;
  padding: 1rem;
  gap: 1rem;
}

.combat-panel {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 10px;
  padding: 1rem;
  border: 1px solid #333;
}

.combat-panel h3 {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Players Panel */
.players-panel {
  width: 220px;
  display: flex;
  flex-direction: column;
}

.combatants-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  overflow-y: auto;
}

.combatant-card {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  position: relative;
}

.combatant-card.is-current-turn {
  border-color: #ffd700;
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
}

.combatant-card.is-you {
  background: rgba(52, 152, 219, 0.15);
}

.combatant-symbol {
  font-size: 1.5rem;
  font-family: monospace;
  font-weight: bold;
  width: 2rem;
  text-align: center;
}

.combatant-info {
  flex: 1;
  min-width: 0;
}

.combatant-name {
  font-size: 0.85rem;
  font-weight: bold;
  color: #fff;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hp-bar-container {
  height: 16px;
  background: #333;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
}

.hp-bar {
  height: 100%;
  background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
  border-radius: 8px;
  transition: width 0.3s ease;
}

.hp-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.7rem;
  font-weight: bold;
  color: #fff;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8);
}

.turn-indicator {
  color: #ffd700;
  font-size: 1.2rem;
  animation: glow 1s infinite;
}

@keyframes glow {
  0%, 100% { text-shadow: 0 0 10px #ffd700; }
  50% { text-shadow: 0 0 20px #ffd700, 0 0 30px #ffd700; }
}

.btn-join-fight {
  margin-top: 0.75rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, #27ae60 0%, #1e8449 100%);
  border: none;
  border-radius: 6px;
  color: white;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-join-fight:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(39, 174, 96, 0.4);
}

/* Center Panel */
.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.turn-indicator-large {
  text-align: center;
  padding: 1rem;
  margin-bottom: 0.75rem;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 8px;
  font-size: 1.2rem;
  font-weight: bold;
}

.your-turn {
  color: #ffd700;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
  animation: yourTurnPulse 1s infinite;
}

@keyframes yourTurnPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.monster-turn {
  color: #e74c3c;
}

.waiting {
  color: #888;
}

/* Simple dice rolling animation in log */
.log-entry.rolling {
  color: #ffd700;
  font-weight: bold;
  font-size: 1.1em;
  animation: rollingPulse 0.3s infinite;
}

@keyframes rollingPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.combat-log {
  flex: 1;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 8px;
  padding: 0.75rem;
  font-family: monospace;
  font-size: 0.8rem;
}

.log-entry {
  padding: 0.35rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #aaa;
}

.log-entry:first-child {
  padding-top: 0;
}

.log-entry:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.log-entry.system {
  color: #3498db;
}

.log-entry.action {
  color: #2ecc71;
}

.log-entry.damage {
  color: #e74c3c;
  font-weight: bold;
}

.log-entry.hit {
  color: #27ae60;
}

.log-entry.miss {
  color: #95a5a6;
  font-style: italic;
}

.log-entry.critical {
  color: #f1c40f;
  font-weight: bold;
  text-shadow: 0 0 10px rgba(241, 196, 15, 0.5);
  animation: criticalFlash 0.5s ease-out;
}

@keyframes criticalFlash {
  0% { background: rgba(241, 196, 15, 0.3); }
  100% { background: transparent; }
}

.log-entry.defend {
  color: #3498db;
}

.log-entry.heal {
  color: #2ecc71;
  font-weight: bold;
}

.log-entry.info {
  color: #888;
}

.log-entry.enemy_hit,
.log-entry.enemy_damage,
.log-entry.enemy_critical {
  color: #e74c3c;
}

.log-entry.enemy_critical {
  font-weight: bold;
  text-shadow: 0 0 10px rgba(231, 76, 60, 0.5);
}

.log-entry.enemy_miss {
  color: #27ae60;
  font-style: italic;
}

.log-entry.victory {
  color: #f1c40f;
  font-weight: bold;
  font-size: 1.1em;
  text-align: center;
  text-shadow: 0 0 15px rgba(241, 196, 15, 0.5);
}

.log-entry.defeat, .log-entry.death {
  color: #e74c3c;
  font-weight: bold;
  font-size: 1.1em;
  text-align: center;
  text-shadow: 0 0 15px rgba(231, 76, 60, 0.5);
}

.log-entry.timeout {
  color: #f39c12;
  font-weight: bold;
  font-size: 1.1em;
  text-align: center;
  text-shadow: 0 0 15px rgba(243, 156, 18, 0.5);
}

.log-empty {
  color: #555;
  font-style: italic;
  text-align: center;
  padding: 2rem;
}

/* Monster Panel */
.monster-panel {
  width: 220px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.monster-panel h3 {
  color: #e74c3c;
}

.monster-card {
  flex-direction: column;
  text-align: center;
  padding: 0.75rem;
}

.monster-symbol-large {
  font-size: 2.5rem;
  font-family: monospace;
  font-weight: bold;
  text-shadow: 0 0 20px currentColor;
  margin-bottom: 0.25rem;
}

.monster-name {
  font-size: 1rem;
  font-weight: bold;
  color: #ffd700;
  margin-bottom: 0.4rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Large Monster HP Display */
.monster-hp-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.2rem;
  margin-bottom: 0.5rem;
  padding: 0.4rem 0.75rem;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 8px;
  border: 1px solid #e74c3c;
}

.hp-icon {
  font-size: 1rem;
}

.hp-current {
  font-size: 1.5rem;
  font-weight: bold;
  color: #e74c3c;
  text-shadow: 0 0 10px rgba(231, 76, 60, 0.5);
  min-width: 2rem;
  text-align: right;
}

.hp-current.hp-low {
  color: #f39c12;
  animation: hpPulse 1s infinite;
}

.hp-current.hp-critical {
  color: #c0392b;
  animation: hpPulse 0.5s infinite;
}

@keyframes hpPulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.05); }
}

.hp-separator {
  font-size: 1rem;
  color: #888;
}

.hp-max {
  font-size: 1rem;
  color: #888;
}

.monster-hp {
  height: 12px;
  margin-top: 0.25rem;
}

.monster-hp .hp-bar {
  background: linear-gradient(90deg, #c0392b 0%, #e74c3c 100%);
}

.monster-hp .hp-bar.hp-bar-low {
  background: linear-gradient(90deg, #d35400 0%, #f39c12 100%);
}

.monster-hp .hp-bar.hp-bar-critical {
  background: linear-gradient(90deg, #7b241c 0%, #c0392b 100%);
  animation: barPulse 0.5s infinite;
}

@keyframes barPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.monster-stats-compact {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 0.5rem;
  padding: 0.4rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
}

.stat-row {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-name {
  font-size: 0.6rem;
  color: #888;
  text-transform: uppercase;
}

.stat-val {
  font-size: 0.85rem;
  font-weight: bold;
  color: #fff;
}

.monster-abilities {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.25rem;
  margin-top: 0.75rem;
  overflow: hidden;
}

.ability-row {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.2rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  min-width: 0;
}

.ability-name {
  font-size: 0.55rem;
  color: #888;
  white-space: nowrap;
}

.ability-mod {
  font-size: 0.7rem;
  font-weight: bold;
  color: #e74c3c;
}

.ability-mod.positive {
  color: #2ecc71;
}

/* Footer */
.combat-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #333;
  background: rgba(0, 0, 0, 0.3);
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.action-btn {
  padding: 0.75rem 1.5rem;
  font-size: 0.95rem;
  font-weight: bold;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 120px;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

.action-btn.attack {
  background: linear-gradient(135deg, #c0392b 0%, #8b0000 100%);
  color: white;
}

.action-btn.attack:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(192, 57, 43, 0.5);
}

.action-btn.defend {
  background: linear-gradient(135deg, #2980b9 0%, #1a5276 100%);
  color: white;
}

.action-btn.defend:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(41, 128, 185, 0.5);
}

.action-btn.item {
  background: linear-gradient(135deg, #8e44ad 0%, #5b2c6f 100%);
  color: white;
}

.action-btn.item:not(:disabled):hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(142, 68, 173, 0.5);
}

.action-btn.flee {
  background: linear-gradient(135deg, #555 0%, #333 100%);
  color: #ccc;
}

.action-btn.flee:not(:disabled):hover {
  transform: translateY(-2px);
  background: linear-gradient(135deg, #666 0%, #444 100%);
}

.action-hint {
  text-align: center;
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: #666;
}

/* Transition */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

/* Scrollbar */
.combat-log::-webkit-scrollbar,
.combatants-list::-webkit-scrollbar {
  width: 6px;
}

.combat-log::-webkit-scrollbar-track,
.combatants-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
}

.combat-log::-webkit-scrollbar-thumb,
.combatants-list::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

/* Victory/Defeat Result Overlay */
.fight-result-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  min-height: 400px;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 16px;
  z-index: 10;
  animation: resultFadeIn 0.5s ease-out;
}

@keyframes resultFadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.fight-result-content {
  text-align: center;
  padding: 3rem;
  animation: resultBounce 0.6s ease-out;
}

@keyframes resultBounce {
  0% {
    opacity: 0;
    transform: scale(0.5);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.fight-result-content.victory .result-icon {
  animation: victoryGlow 2s ease-in-out infinite;
}

@keyframes victoryGlow {
  0%, 100% {
    text-shadow: 0 0 20px rgba(255, 215, 0, 0.8), 0 0 40px rgba(255, 215, 0, 0.4);
  }
  50% {
    text-shadow: 0 0 40px rgba(255, 215, 0, 1), 0 0 80px rgba(255, 215, 0, 0.6);
  }
}

.fight-result-content.defeat .result-icon {
  animation: defeatPulse 2s ease-in-out infinite;
}

@keyframes defeatPulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.result-icon {
  font-size: 5rem;
  margin-bottom: 1rem;
}

.result-title {
  font-size: 3rem;
  font-weight: bold;
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: 4px;
}

.fight-result-content.victory .result-title {
  color: #ffd700;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
}

.fight-result-content.defeat .result-title {
  color: #e74c3c;
  text-shadow: 0 0 20px rgba(231, 76, 60, 0.5);
}

.result-message {
  font-size: 1.3rem;
  color: #bdc3c7;
  margin-bottom: 1.5rem;
}

.result-rewards {
  margin-bottom: 2rem;
  padding: 1rem 2rem;
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 10px;
  display: inline-block;
}

.reward-item {
  font-size: 1.1rem;
  color: #ffd700;
}

.btn-continue {
  padding: 1rem 2.5rem;
  font-size: 1.2rem;
  font-weight: bold;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 1rem;
}

.fight-result-content.victory .btn-continue {
  background: linear-gradient(135deg, #f1c40f 0%, #f39c12 100%);
  color: #1a1a1a;
  box-shadow: 0 4px 20px rgba(241, 196, 15, 0.4);
}

.fight-result-content.victory .btn-continue:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 30px rgba(241, 196, 15, 0.6);
}

.fight-result-content.defeat .btn-continue {
  background: linear-gradient(135deg, #555 0%, #333 100%);
  color: #ccc;
}

.fight-result-content.defeat .btn-continue:hover {
  transform: translateY(-3px);
  background: linear-gradient(135deg, #666 0%, #444 100%);
}
</style>
