import { createRouter, createWebHistory } from 'vue-router'

import OverviewView from './views/OverviewView.vue'
import PortfolioView from './views/PortfolioView.vue'
import TradesSignalsView from './views/TradesSignalsView.vue'
import AiModelsView from './views/AiModelsView.vue'
import RiskSafetyView from './views/RiskSafetyView.vue'
import SystemHealthView from './views/SystemHealthView.vue'

const routes = [
  { path: '/', redirect: '/overview' },
  { path: '/overview', component: OverviewView },
  { path: '/portfolio', component: PortfolioView },
  { path: '/trades-signals', component: TradesSignalsView },
  { path: '/ai-models', component: AiModelsView },
  { path: '/risk-safety', component: RiskSafetyView },
  { path: '/system-health', component: SystemHealthView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
