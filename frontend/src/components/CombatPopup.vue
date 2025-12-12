<template>
  <transition name="popup-fade">
    <div class="combat-popup-overlay" v-if="show && monster" @click="$emit('decline')">
      <div class="combat-popup-card" @click.stop>
        <div class="popup-header">
          <span class="popup-icon">⚔️</span>
          <h2>Combat Encounter!</h2>
        </div>
        
        <div class="monster-display">
          <div class="monster-symbol" :style="{ color: monster.color }">
            {{ monster.symbol }}
          </div>
          <h3 class="monster-name">{{ monster.name }}</h3>
          <p class="monster-description" v-if="monster.description">
            {{ monster.description }}
          </p>
        </div>
        
        <div class="monster-stats">
          <h4>Monster Stats</h4>
          <div class="stats-grid">
            <div class="stat-item hp">
              <span class="stat-label">HP</span>
              <span class="stat-value">{{ monster.stats.hp }}/{{ monster.stats.max_hp }}</span>
            </div>
            <div class="stat-item ac">
              <span class="stat-label">AC</span>
              <span class="stat-value">{{ monster.stats.ac }}</span>
            </div>
          </div>
          
          <div class="abilities-grid">
            <div class="ability-item" v-for="ability in abilities" :key="ability.name">
              <span class="ability-name">{{ ability.name }}</span>
              <span class="ability-value" :class="{ positive: ability.modifier >= 0, negative: ability.modifier < 0 }">
                {{ ability.value }} ({{ ability.modifier >= 0 ? '+' : '' }}{{ ability.modifier }})
              </span>
            </div>
          </div>
          
          <div class="challenge-rating" v-if="monster.stats.challenge_rating">
            <span class="cr-label">Challenge Rating:</span>
            <span class="cr-value">{{ monster.stats.challenge_rating }}</span>
          </div>
        </div>
        
        <div class="popup-actions">
          <button class="btn-accept" @click="$emit('accept')">
            ⚔️ Fight!
          </button>
          <button class="btn-decline" @click="$emit('decline')">
            🚪 Retreat
          </button>
        </div>
        
        <div class="popup-hint">
          Press <kbd>Enter</kbd> to fight or <kbd>Esc</kbd> to retreat
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
import { computed, onMounted, onUnmounted } from 'vue'

export default {
  name: 'CombatPopup',
  props: {
    show: {
      type: Boolean,
      default: false
    },
    monster: {
      type: Object,
      default: null
    }
  },
  emits: ['accept', 'decline'],
  setup(props, { emit }) {
    // Calculate ability modifiers (D&D formula: (stat - 10) // 2)
    const getModifier = (value) => Math.floor((value - 10) / 2)
    
    const abilities = computed(() => {
      if (!props.monster?.stats) return []
      const stats = props.monster.stats
      return [
        { name: 'STR', value: stats.str || 10, modifier: getModifier(stats.str || 10) },
        { name: 'DEX', value: stats.dex || 10, modifier: getModifier(stats.dex || 10) },
        { name: 'CON', value: stats.con || 10, modifier: getModifier(stats.con || 10) },
        { name: 'INT', value: stats.int || 10, modifier: getModifier(stats.int || 10) },
        { name: 'WIS', value: stats.wis || 10, modifier: getModifier(stats.wis || 10) },
        { name: 'CHA', value: stats.cha || 10, modifier: getModifier(stats.cha || 10) }
      ]
    })
    
    // Keyboard handling
    const handleKeyDown = (e) => {
      if (!props.show || !props.monster) return
      
      if (e.key === 'Enter') {
        e.preventDefault()
        emit('accept')
      } else if (e.key === 'Escape') {
        e.preventDefault()
        emit('decline')
      }
    }
    
    onMounted(() => {
      window.addEventListener('keydown', handleKeyDown)
    })
    
    onUnmounted(() => {
      window.removeEventListener('keydown', handleKeyDown)
    })
    
    return {
      abilities
    }
  }
}
</script>

<style scoped>
.combat-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(5px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1500;
  cursor: pointer;
}

.combat-popup-card {
  background: linear-gradient(135deg, rgba(44, 24, 16, 0.95) 0%, rgba(26, 15, 10, 0.95) 100%);
  backdrop-filter: blur(20px);
  border: 3px solid rgba(231, 76, 60, 0.6);
  border-radius: 16px;
  padding: 1.5rem 2rem;
  max-width: 450px;
  width: 90%;
  text-align: center;
  box-shadow: 0 0 50px rgba(231, 76, 60, 0.4), 0 0 100px rgba(231, 76, 60, 0.2), inset 0 0 30px rgba(0, 0, 0, 0.5);
  cursor: default;
  animation: cardAppear 0.3s ease-out;
}

@keyframes cardAppear {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.popup-header {
  margin-bottom: 1rem;
}

.popup-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 0.5rem;
  filter: drop-shadow(0 0 10px rgba(231, 76, 60, 0.5));
}

.popup-header h2 {
  font-size: 1.6rem;
  color: #e74c3c;
  margin: 0;
  text-shadow: 0 0 20px rgba(231, 76, 60, 0.5), 2px 2px 4px rgba(0, 0, 0, 0.8);
  font-weight: 700;
}

.monster-display {
  margin-bottom: 1rem;
}

.monster-symbol {
  font-size: 4rem;
  font-family: monospace;
  font-weight: bold;
  text-shadow: 0 0 20px currentColor;
  margin-bottom: 0.5rem;
}

.monster-name {
  font-size: 1.3rem;
  color: #ffd700;
  margin: 0 0 0.5rem 0;
}

.monster-description {
  font-size: 0.85rem;
  color: #aaa;
  font-style: italic;
  line-height: 1.4;
  margin: 0;
}

.monster-stats {
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.monster-stats h4 {
  color: #ffd700;
  margin: 0 0 0.75rem 0;
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
  font-weight: 700;
}

.stats-grid {
  display: flex;
  justify-content: center;
  gap: 2rem;
  margin-bottom: 0.75rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-item.hp .stat-value {
  color: #e74c3c;
}

.stat-item.ac .stat-value {
  color: #3498db;
}

.stat-label {
  font-size: 0.7rem;
  color: #888;
  text-transform: uppercase;
}

.stat-value {
  font-size: 1.2rem;
  font-weight: bold;
  color: #fff;
}

.abilities-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.ability-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.3rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(155, 89, 182, 0.3);
  border-radius: 6px;
  transition: all 0.2s ease;
}

.ability-item:hover {
  border-color: rgba(155, 89, 182, 0.5);
  transform: translateY(-1px);
}

.ability-name {
  font-size: 0.65rem;
  color: #9b59b6;
  text-transform: uppercase;
  font-weight: 700;
}

.ability-value {
  font-size: 0.85rem;
  font-weight: 700;
  color: #ffd700;
}

.ability-value.positive {
  color: #2ecc71;
}

.ability-value.negative {
  color: #e74c3c;
}

.challenge-rating {
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.cr-label {
  color: #888;
}

.cr-value {
  color: #f39c12;
  font-weight: bold;
}

.popup-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  margin-bottom: 1rem;
}

.popup-actions button {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  font-weight: bold;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-accept {
  background: linear-gradient(135deg, #c0392b 0%, #8b0000 100%);
  color: white;
  box-shadow: 0 4px 15px rgba(192, 57, 43, 0.4);
}

.btn-accept:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(192, 57, 43, 0.6);
}

.btn-decline {
  background: linear-gradient(135deg, #555 0%, #333 100%);
  color: #ccc;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.btn-decline:hover {
  transform: translateY(-2px);
  background: linear-gradient(135deg, #666 0%, #444 100%);
}

.popup-hint {
  font-size: 0.75rem;
  color: #666;
}

.popup-hint kbd {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  font-family: monospace;
  font-size: 0.7rem;
  color: #ffd700;
  font-weight: 600;
}

/* Transition */
.popup-fade-enter-active,
.popup-fade-leave-active {
  transition: opacity 0.3s ease;
}

.popup-fade-enter-from,
.popup-fade-leave-to {
  opacity: 0;
}
</style>
