import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import LobbyPage from '../pages/LobbyPage.vue'
import GamePage from '../pages/GamePage.vue'
import ArenaPage from '../pages/ArenaPage.vue'
import { usePlayerStore } from '../stores/playerStore'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
    meta: { requiresAuth: false }
  },
  {
    path: '/lobby',
    name: 'lobby',
    component: LobbyPage,
    meta: { requiresAuth: true }
  },
  {
    path: '/game/:gameId',
    name: 'game',
    component: GamePage,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    // Legacy route - redirect to lobby
    path: '/game',
    redirect: '/lobby'
  },
  {
    path: '/arena',
    name: 'arena',
    component: ArenaPage,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory('/static/'),
  routes
})

// Navigation guard to check authentication
router.beforeEach(async (to, from, next) => {
  const playerStore = usePlayerStore()
  
  // Check if route requires authentication
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  
  // If route requires auth and user is not authenticated
  if (requiresAuth && !playerStore.isAuthenticated) {
    // Try to fetch current user (in case they have a valid cookie)
    const authenticated = await playerStore.fetchCurrentUser()
    
    if (!authenticated) {
      // Redirect to home page
      next({ name: 'home' })
      return
    }
  }
  
  // If user is authenticated and trying to access home, redirect to lobby
  if (to.name === 'home' && playerStore.isAuthenticated) {
    next({ name: 'lobby' })
    return
  }
  
  next()
})

export default router
