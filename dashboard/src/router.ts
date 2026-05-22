import { createRouter, createWebHistory } from 'vue-router'

import OverviewView from './views/OverviewView.vue'
import TradesSignalsView from './views/TradesSignalsView.vue'
import RiskSafetyView from './views/RiskSafetyView.vue'
import SystemHealthView from './views/SystemHealthView.vue'

const routes = [
  { path: '/', redirect: '/overview' },
  { path: '/overview', component: OverviewView },
  { path: '/portfolio', redirect: '/overview' },
  { path: '/trades-signals', component: TradesSignalsView },
  { path: '/ai-models', redirect: '/overview' },
  { path: '/risk-safety', component: RiskSafetyView },
  { path: '/system-health', component: SystemHealthView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
