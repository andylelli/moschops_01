import { createRouter, createWebHistory } from 'vue-router'

import OverviewView from './views/OverviewView.vue'
import PortfolioView from './views/PortfolioView.vue'
import TradesSignalsView from './views/TradesSignalsView.vue'
import AiModelsView from './views/AiModelsView.vue'
import TrainingStudioView from './views/TrainingStudioView.vue'
import RiskSafetyView from './views/RiskSafetyView.vue'
import SystemHealthView from './views/SystemHealthView.vue'
import IncidentsRunbooksView from './views/IncidentsRunbooksView.vue'
import AdminView from './views/AdminView.vue'
import SettingsView from './views/SettingsView.vue'

const routes = [
  { path: '/', redirect: '/overview' },
  { path: '/overview', component: OverviewView },
  { path: '/portfolio', component: PortfolioView },
  { path: '/trades-signals', component: TradesSignalsView },
  { path: '/ai-models', component: AiModelsView },
  { path: '/training-studio', component: TrainingStudioView },
  { path: '/risk-safety', component: RiskSafetyView },
  { path: '/system-health', component: SystemHealthView },
  { path: '/incidents-runbooks', component: IncidentsRunbooksView },
  { path: '/admin', component: AdminView, meta: { allowedRoles: ['analyst', 'admin'] } },
  { path: '/settings', component: SettingsView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const allowedRoles = Array.isArray(to.meta.allowedRoles) ? (to.meta.allowedRoles as string[]) : null
  if (!allowedRoles) {
    return true
  }

  const activeRole = localStorage.getItem('moschops-role') ?? 'analyst'
  if (allowedRoles.includes(activeRole)) {
    return true
  }

  return '/overview'
})

export default router
