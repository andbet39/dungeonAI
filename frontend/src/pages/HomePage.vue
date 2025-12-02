<template>
  <div class="home-container">
    <div class="home-content">
      <!-- Header -->
      <div class="home-header">
        <h1 class="home-title">
          <span class="title-icon">🗡️</span>
          DungeonAI
        </h1>
        <p class="home-subtitle">Enter the depths where monsters learn and adapt</p>
      </div>

      <!-- Navigation Cards -->
      <div class="nav-cards">
        <!-- Game Card -->
        <router-link to="/lobby" class="nav-card game-card">
          <div class="card-icon">🏰</div>
          <div class="card-content">
            <h2>Enter Dungeon</h2>
            <p>Explore procedurally generated dungeons, battle intelligent monsters, and survive the depths.</p>
            <ul class="card-features">
              <li>🗺️ Procedural dungeon generation</li>
              <li>⚔️ Real-time multiplayer combat</li>
              <li>🧠 AI-powered monster behavior</li>
              <li>👥 Up to 4 players per game</li>
            </ul>
          </div>
          <div class="card-action">
            <span class="action-text">Find a Game</span>
            <span class="action-arrow">→</span>
          </div>
        </router-link>

        <!-- Arena Card -->
        <router-link to="/arena" class="nav-card arena-card">
          <div class="card-icon">🧠</div>
          <div class="card-content">
            <h2>AI Arena</h2>
            <p>Debug and test the monster intelligence system. View learning progress and simulate decisions.</p>
            <ul class="card-features">
              <li>📊 Species knowledge tables</li>
              <li>🎭 Personality profiles</li>
              <li>🔬 Decision simulation</li>
            </ul>
          </div>
          <div class="card-action">
            <span class="action-text">Open Arena</span>
            <span class="action-arrow">→</span>
          </div>
        </router-link>
      </div>

      <!-- Footer Info -->
      <div class="home-footer">
        <div class="footer-section">
          <h3>🎮 Controls</h3>
          <p><kbd>↑</kbd> <kbd>↓</kbd> <kbd>←</kbd> <kbd>→</kbd> or <kbd>HJKL</kbd> to move</p>
          <p><kbd>Space</kbd> or <kbd>E</kbd> to interact</p>
        </div>
        <div class="footer-section">
          <h3>🧬 Monster AI</h3>
          <p>Monsters use Q-learning to adapt their combat strategies based on experience.</p>
          <p>Each species shares knowledge across generations.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HomePage'
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f0f23 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem;
}

.home-content {
  max-width: 1000px;
  width: 100%;
}

.home-header {
  text-align: center;
  margin-bottom: 3rem;
}

.home-title {
  font-size: 3.5rem;
  color: #ffd700;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.4);
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.title-icon {
  font-size: 4rem;
  animation: sword-glow 2s ease-in-out infinite;
}

@keyframes sword-glow {
  0%, 100% { filter: drop-shadow(0 0 10px rgba(255, 215, 0, 0.6)); }
  50% { filter: drop-shadow(0 0 20px rgba(255, 215, 0, 0.9)); }
}

.home-subtitle {
  font-size: 1.3rem;
  color: #7f8c8d;
  font-style: italic;
}

.nav-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 2rem;
  margin-bottom: 3rem;
}

.nav-card {
  background: linear-gradient(135deg, #2c3e50 0%, #1a1a2e 100%);
  border-radius: 16px;
  padding: 2rem;
  text-decoration: none;
  color: inherit;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.nav-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, transparent 0%, rgba(255, 255, 255, 0.05) 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.nav-card:hover::before {
  opacity: 1;
}

.game-card:hover {
  border-color: #e74c3c;
  box-shadow: 0 0 30px rgba(231, 76, 60, 0.3);
  transform: translateY(-5px);
}

.arena-card:hover {
  border-color: #9b59b6;
  box-shadow: 0 0 30px rgba(155, 89, 182, 0.3);
  transform: translateY(-5px);
}

.card-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.card-content h2 {
  font-size: 1.8rem;
  margin-bottom: 0.5rem;
}

.game-card .card-content h2 {
  color: #e74c3c;
}

.arena-card .card-content h2 {
  color: #9b59b6;
}

.card-content p {
  color: #bdc3c7;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.card-features {
  list-style: none;
  padding: 0;
  margin: 0;
}

.card-features li {
  padding: 0.3rem 0;
  color: #95a5a6;
  font-size: 0.9rem;
}

.card-action {
  margin-top: auto;
  padding-top: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #333;
}

.action-text {
  font-weight: bold;
  font-size: 1.1rem;
}

.game-card .action-text {
  color: #e74c3c;
}

.arena-card .action-text {
  color: #9b59b6;
}

.action-arrow {
  font-size: 1.5rem;
  transition: transform 0.3s ease;
}

.nav-card:hover .action-arrow {
  transform: translateX(5px);
}

.home-footer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
}

.footer-section h3 {
  color: #3498db;
  margin-bottom: 0.5rem;
  font-size: 1rem;
}

.footer-section p {
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-bottom: 0.3rem;
}

kbd {
  background: #1a1a1a;
  border: 1px solid #555;
  border-radius: 4px;
  padding: 0.2rem 0.5rem;
  font-family: monospace;
  font-size: 0.8rem;
  color: #ecf0f1;
}
</style>
