<template>
  <section class="stats-section" v-if="myPlayer">
    <h2>⚔️ Your Stats</h2>
    <div class="hp-bar-container">
      <div class="hp-bar" :style="{ width: hpPercentage + '%' }" :class="hpBarClass"></div>
      <span class="hp-text">❤️ {{ myPlayer.hp }} / {{ myPlayer.max_hp }}</span>
    </div>
    <div class="stats-grid">
      <div class="stat-box">
        <span class="stat-label">🛡️ AC</span>
        <span class="stat-value">{{ myPlayer.effective_ac || myPlayer.ac }}</span>
        <span class="stat-note" v-if="myPlayer.is_defending">+2 def</span>
      </div>
      <div class="stat-box">
        <span class="stat-label">⚔️ DMG</span>
        <span class="stat-value">{{ myPlayer.damage_dice }}</span>
      </div>
    </div>
    <div class="ability-scores">
      <div class="ability">
        <span class="ability-name">STR</span>
        <span class="ability-score">{{ myPlayer.str }}</span>
        <span class="ability-mod">({{ formatMod(myPlayer.str_mod) }})</span>
      </div>
      <div class="ability">
        <span class="ability-name">DEX</span>
        <span class="ability-score">{{ myPlayer.dex }}</span>
        <span class="ability-mod">({{ formatMod(myPlayer.dex_mod) }})</span>
      </div>
      <div class="ability">
        <span class="ability-name">CON</span>
        <span class="ability-score">{{ myPlayer.con }}</span>
        <span class="ability-mod">({{ formatMod(myPlayer.con_mod) }})</span>
      </div>
    </div>
    <div class="status-effects" v-if="myPlayer.is_defending">
      <span class="status-badge defending">🛡️ Defending</span>
    </div>
  </section>
</template>

<script>
import { storeToRefs } from 'pinia'
import { usePlayerStore } from '../../stores/playerStore'

export default {
  name: 'PlayerStatsPanel',
  setup() {
    const playerStore = usePlayerStore()
    const { myPlayer, hpPercentage, hpBarClass } = storeToRefs(playerStore)
    const { formatMod } = playerStore

    return {
      myPlayer,
      hpPercentage,
      hpBarClass,
      formatMod
    }
  }
}
</script>

<style scoped>
.stats-section {
  background: linear-gradient(135deg, #1a2a3a 0%, #1a1a2e 100%);
  border-radius: 8px;
  padding: 0.6rem;
  border: 1px solid #3498db;
}

.stats-section h2 {
  font-size: 0.85rem;
  color: #e74c3c;
  margin-bottom: 0.3rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #e74c3c;
}

.hp-bar-container {
  position: relative;
  height: 22px;
  background: #333;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  overflow: hidden;
  border: 1px solid #555;
}

.hp-bar {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
  border-radius: 3px;
}

.hp-bar.hp-high {
  background: linear-gradient(90deg, #27ae60, #2ecc71);
}

.hp-bar.hp-medium {
  background: linear-gradient(90deg, #f39c12, #f1c40f);
}

.hp-bar.hp-low {
  background: linear-gradient(90deg, #c0392b, #e74c3c);
  animation: pulse-low 1s ease-in-out infinite;
}

@keyframes pulse-low {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
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

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.stat-box {
  background: #1a1a1a;
  border-radius: 4px;
  padding: 0.4rem;
  text-align: center;
  border: 1px solid #444;
}

.stat-label {
  display: block;
  font-size: 0.6rem;
  color: #95a5a6;
  margin-bottom: 0.1rem;
}

.stat-value {
  display: block;
  font-size: 1rem;
  font-weight: bold;
  color: #ecf0f1;
}

.stat-note {
  display: block;
  font-size: 0.55rem;
  color: #3498db;
  margin-top: 0.1rem;
}

.ability-scores {
  display: flex;
  justify-content: space-between;
  gap: 0.3rem;
  margin-bottom: 0.4rem;
}

.ability {
  flex: 1;
  background: #1a1a1a;
  border-radius: 4px;
  padding: 0.3rem;
  text-align: center;
  border: 1px solid #444;
}

.ability-name {
  display: block;
  font-size: 0.55rem;
  color: #9b59b6;
  font-weight: bold;
}

.ability-score {
  display: block;
  font-size: 0.85rem;
  font-weight: bold;
  color: #ecf0f1;
}

.ability-mod {
  display: block;
  font-size: 0.6rem;
  color: #3498db;
}

.status-effects {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.status-badge {
  font-size: 0.6rem;
  padding: 0.15rem 0.4rem;
  border-radius: 10px;
  font-weight: bold;
}

.status-badge.defending {
  background: linear-gradient(135deg, #2980b9, #3498db);
  color: #fff;
  animation: defending-glow 1.5s ease-in-out infinite;
}

@keyframes defending-glow {
  0%, 100% { box-shadow: 0 0 5px rgba(52, 152, 219, 0.5); }
  50% { box-shadow: 0 0 10px rgba(52, 152, 219, 0.8); }
}
</style>
