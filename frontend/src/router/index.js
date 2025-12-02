import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import LobbyPage from '../pages/LobbyPage.vue'
import GamePage from '../pages/GamePage.vue'
import ArenaPage from '../pages/ArenaPage.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage
  },
  {
    path: '/lobby',
    name: 'lobby',
    component: LobbyPage
  },
  {
    path: '/game/:gameId',
    name: 'game',
    component: GamePage,
    props: true
  },
  {
    // Legacy route - redirect to lobby
    path: '/game',
    redirect: '/lobby'
  },
  {
    path: '/arena',
    name: 'arena',
    component: ArenaPage
  }
]

const router = createRouter({
  history: createWebHistory('/static/'),
  routes
})

export default router
