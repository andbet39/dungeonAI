<template>
  <div class="home-container">
    <!-- Animated Background Elements -->
    <div class="bg-decorations">
      <div class="decoration decoration-1"></div>
      <div class="decoration decoration-2"></div>
      <div class="decoration decoration-3"></div>
    </div>

    <div class="home-content">
      <!-- Header -->
      <div class="home-header">
        <div class="logo-container">
          <span class="title-icon">🗡️</span>
          <h1 class="home-title">DungeonAI</h1>
        </div>
        <p class="home-subtitle">Enter the depths where monsters learn and adapt</p>
        <div class="feature-badges">
          <span class="badge">🧠 AI Monsters</span>
          <span class="badge">⚔️ Multiplayer</span>
          <span class="badge">🗺️ Procedural</span>
        </div>
      </div>

      <!-- Auth Forms -->
      <div class="auth-container">
        <div class="auth-toggle">
          <button 
            :class="['toggle-btn', { active: showLogin }]"
            @click="showLogin = true"
          >
            <span class="toggle-icon">🔓</span> Login
          </button>
          <button 
            :class="['toggle-btn', { active: !showLogin }]"
            @click="showLogin = false"
          >
            <span class="toggle-icon">✨</span> Register
          </button>
        </div>

        <transition name="slide-fade" mode="out-in">
          <LoginForm 
            v-if="showLogin" 
            @switch-to-register="showLogin = false"
          />
          <RegisterForm 
            v-else 
            @switch-to-login="showLogin = true"
          />
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import LoginForm from '../components/LoginForm.vue'
import RegisterForm from '../components/RegisterForm.vue'

const showLogin = ref(true)
</script>

<style scoped>
.home-container {
  position: relative;
  height: 100vh;
  background: radial-gradient(ellipse at top, #1e2749 0%, #16213e 40%, #0f1419 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2rem;
  overflow: hidden;
}

/* Animated Background Decorations */
.bg-decorations {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 0;
}

.decoration {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.15;
  animation: float 20s infinite ease-in-out;
}

.decoration-1 {
  width: 400px;
  height: 400px;
  background: #ffd700;
  top: -100px;
  left: -100px;
  animation-delay: 0s;
}

.decoration-2 {
  width: 300px;
  height: 300px;
  background: #9b59b6;
  bottom: -50px;
  right: -50px;
  animation-delay: -7s;
}

.decoration-3 {
  width: 350px;
  height: 350px;
  background: #3498db;
  top: 50%;
  right: 10%;
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
}

.home-content {
  position: relative;
  z-index: 1;
  max-width: 550px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.home-header {
  text-align: center;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.title-icon {
  font-size: 3.5rem;
  animation: sword-glow 3s ease-in-out infinite;
}

@keyframes sword-glow {
  0%, 100% { 
    filter: drop-shadow(0 0 15px rgba(255, 215, 0, 0.7));
    transform: rotate(-5deg);
  }
  50% { 
    filter: drop-shadow(0 0 25px rgba(255, 215, 0, 1));
    transform: rotate(5deg);
  }
}

.home-title {
  font-size: 3.5rem;
  font-weight: 900;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 50%, #ffd700 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 4px 20px rgba(255, 215, 0, 0.3);
  letter-spacing: -0.02em;
}

.home-subtitle {
  font-size: 1.15rem;
  color: #a0aec0;
  font-weight: 300;
  letter-spacing: 0.02em;
  margin-bottom: 1rem;
}

.feature-badges {
  display: flex;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.badge {
  background: rgba(255, 215, 0, 0.1);
  border: 1px solid rgba(255, 215, 0, 0.3);
  border-radius: 20px;
  padding: 0.4rem 1rem;
  color: #ffd700;
  font-size: 0.85rem;
  font-weight: 600;
  backdrop-filter: blur(10px);
  transition: all 0.3s;
}

.badge:hover {
  background: rgba(255, 215, 0, 0.2);
  border-color: #ffd700;
  transform: translateY(-2px);
}

.auth-container {
  width: 100%;
}

.auth-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  background: rgba(20, 25, 40, 0.6);
  border-radius: 12px;
  padding: 0.5rem;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 215, 0, 0.1);
}

.toggle-btn {
  flex: 1;
  background: transparent;
  border: none;
  border-radius: 8px;
  padding: 0.75rem 1.5rem;
  color: #718096;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.toggle-icon {
  font-size: 1.1rem;
}

.toggle-btn.active {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  color: #1a1a2e;
  box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
}

.toggle-btn:not(.active):hover {
  color: #ffd700;
  background: rgba(255, 215, 0, 0.05);
}

/* Slide fade transition */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  transform: translateY(10px);
  opacity: 0;
}

.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

.quick-info {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 1rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  border: 1px solid rgba(255, 215, 0, 0.1);
  backdrop-filter: blur(10px);
}

.info-item {
  color: #a0aec0;
  font-size: 0.85rem;
  font-weight: 500;
}

.info-separator {
  color: rgba(255, 215, 0, 0.3);
  font-weight: 300;
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
