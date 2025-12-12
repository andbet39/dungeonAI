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
  background: rgba(15, 18, 30, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  padding: 0.75rem;
  border: 1px solid rgba(231, 76, 60, 0.4);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.stats-section:hover {
  border-color: rgba(231, 76, 60, 0.6);
}

.stats-section h2 {
  font-size: 0.9rem;
  color: #e74c3c;
  margin-bottom: 0.5rem;
  padding-bottom: 0.375rem;
  border-bottom: 1px solid rgba(231, 76, 60, 0.3);
  font-weight: 700;
  text-shadow: 0 0 10px rgba(231, 76, 60, 0.3);
}

.hp-bar-container {
  position: relative;
  height: 24px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 6px;
  margin-bottom: 0.5rem;
  overflow: hidden;
  border: 1px solid rgba(255, 215, 0, 0.2);
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
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  padding: 0.5rem;
  text-align: center;
  border: 1px solid rgba(255, 215, 0, 0.2);
  transition: all 0.3s ease;
}

.stat-box:hover {
  border-color: rgba(255, 215, 0, 0.35);
  transform: translateY(-1px);
}

.stat-label {
  display: block;
  font-size: 0.65rem;
  color: #a0aec0;
  margin-bottom: 0.15rem;
  font-weight: 500;
}

.stat-value {
  display: block;
  font-size: 1.1rem;
  font-weight: 700;
  color: #ffd700;
  text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
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
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
  padding: 0.4rem;
  text-align: center;
  border: 1px solid rgba(155, 89, 182, 0.3);
  transition: all 0.3s ease;
}

.ability:hover {
  border-color: rgba(155, 89, 182, 0.5);
  transform: translateY(-1px);
}

.ability-name {
  display: block;
  font-size: 0.6rem;
  color: #9b59b6;
  font-weight: 700;
}

.ability-score {
  display: block;
  font-size: 0.9rem;
  font-weight: 700;
  color: #ffd700;
  text-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
}

.ability-mod {
  display: block;
  font-size: 0.65rem;
  color: #5dade2;
  font-weight: 600;
}

.status-effects {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.status-badge {
  font-size: 0.65rem;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-weight: 700;
  background: linear-gradient(135deg, rgba(52, 152, 219, 0.8) 0%, rgba(41, 128, 185, 0.8) 100%);
  border: 1px solid rgba(52, 152, 219, 0.4);
  color: #fff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.status-badge:hover {
  transform: scale(1.05);
}

.status-badge.defending {
  background: linear-gradient(135deg, rgba(41, 128, 185, 0.9) 0%, rgba(52, 152, 219, 0.9) 100%);
  border-color: rgba(52, 152, 219, 0.6);
  color: #fff;
  animation: defending-glow 1.5s ease-in-out infinite;
}

@keyframes defending-glow {
  0%, 100% { 
    box-shadow: 0 0 8px rgba(52, 152, 219, 0.5);
  }
  50% { 
    box-shadow: 0 0 15px rgba(52, 152, 219, 0.8), 0 0 20px rgba(52, 152, 219, 0.4);
  }
}
</style>
