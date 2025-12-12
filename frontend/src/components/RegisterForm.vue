<template>
  <div class="register-form-container">
    <div class="form-card">
      <div class="form-header">
        <h2>🗡️ Join DungeonAI</h2>
        <p>Create your account to start your adventure</p>
      </div>

      <form @submit.prevent="handleSubmit" class="auth-form">
        <div class="form-group">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            autocomplete="email"
            :disabled="loading"
            @input="clearError"
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            minlength="8"
            autocomplete="new-password"
            :disabled="loading"
            @input="clearError"
          />
          <small class="field-hint">Minimum 8 characters</small>
        </div>

        <div class="form-group">
          <label for="confirm-password">Confirm Password</label>
          <input
            id="confirm-password"
            v-model="confirmPassword"
            type="password"
            required
            autocomplete="new-password"
            :disabled="loading"
            @input="clearError"
          />
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>

        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="!loading">Create Account</span>
          <span v-else">Creating Account...</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePlayerStore } from '../stores/playerStore'

const emit = defineEmits(['switch-to-login'])
const router = useRouter()
const playerStore = usePlayerStore()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

const clearError = () => {
  error.value = ''
}

const handleSubmit = async () => {
  error.value = ''
  
  // Validate password match
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }
  
  // Validate password length
  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters long'
    return
  }

  loading.value = true

  try {
    await playerStore.register(email.value, password.value)
    router.push('/lobby')
  } catch (err) {
    error.value = err.message || 'Registration failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-form-container {
  width: 100%;
}

.form-card {
  background: rgba(20, 25, 40, 0.95);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  padding: 2rem;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(20px);
  transition: all 0.3s;
}

.form-card:hover {
  border-color: rgba(255, 215, 0, 0.4);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6), 0 0 40px rgba(255, 215, 0, 0.1);
}

.form-header {
  text-align: center;
  margin-bottom: 1.75rem;
}

.form-header h2 {
  color: #ffd700;
  font-size: 1.6rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  letter-spacing: -0.01em;
}

.form-header p {
  color: #a0aec0;
  font-size: 0.9rem;
  font-weight: 400;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  color: #ffd700;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.form-group input {
  background: rgba(15, 18, 30, 0.8);
  border: 1px solid rgba(255, 215, 0, 0.25);
  border-radius: 8px;
  padding: 0.875rem 1rem;
  color: #fff;
  font-size: 1rem;
  transition: all 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #ffd700;
  background: rgba(15, 18, 30, 0.95);
  box-shadow: 0 0 0 3px rgba(255, 215, 0, 0.1);
}

.form-group input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-hint {
  color: #718096;
  font-size: 0.75rem;
  margin-top: -0.25rem;
}

.error-message {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: 8px;
  padding: 0.875rem;
  color: #fca5a5;
  font-size: 0.875rem;
  animation: shake 0.4s;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.submit-btn {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  border-radius: 8px;
  padding: 1rem;
  color: #1a1a2e;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
  margin-top: 0.5rem;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 215, 0, 0.5);
}

.submit-btn:active:not(:disabled) {
  transform: translateY(0);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
</style>
