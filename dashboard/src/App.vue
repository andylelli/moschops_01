<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useUiStore } from './stores/ui'
import KillSwitchBanner from './components/KillSwitchBanner.vue'
import AlertRail from './components/AlertRail.vue'

const ui = useUiStore()
const route = useRoute()
const isMobileMenuOpen = ref(false)

const alertItems = [
  {
    id: 'ALR-2201',
    severity: 'warning' as const,
    title: 'Provider Freshness Degrading',
    detail: 'News sync latency crossed 2x polling interval in one region.',
    source: 'news-provider',
    timestamp: '2026-05-22T14:25:00Z',
  },
  {
    id: 'ALR-2202',
    severity: 'info' as const,
    title: 'Training Capacity Available',
    detail: 'Queue depth low. Preset launch windows are open.',
    source: 'training-orchestrator',
    timestamp: '2026-05-22T14:20:00Z',
  },
]

const onKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    isMobileMenuOpen.value = false
  }
}

onMounted(() => {
  ui.applyTheme()
  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  document.body.classList.remove('mobile-menu-open')
})

watch(
  () => route.path,
  () => {
    isMobileMenuOpen.value = false
  },
)

watch(isMobileMenuOpen, (open) => {
  document.body.classList.toggle('mobile-menu-open', open)
})

watch(
  () => [ui.environment, ui.strategy, ui.operatorRole, ui.datasetProfile, ui.startDate, ui.endDate],
  () => {
    ui.persistContext()
  },
)

const navItems = [
  { to: '/overview', label: 'Overview', icon: 'gauge-high' },
  { to: '/portfolio', label: 'Portfolio', icon: 'briefcase' },
  { to: '/trades-signals', label: 'Trades and Signals', icon: 'arrow-right-arrow-left' },
  { to: '/ai-models', label: 'AI and Models', icon: 'microchip' },
  { to: '/training-studio', label: 'Training Studio', icon: 'flask' },
  { to: '/risk-safety', label: 'Risk and Safety', icon: 'shield-halved' },
  { to: '/system-health', label: 'System Health', icon: 'heartbeat' },
  { to: '/incidents-runbooks', label: 'Incidents and Runbooks', icon: 'triangle-exclamation' },
  { to: '/admin', label: 'Admin', icon: 'user-shield' },
  { to: '/settings', label: 'Settings', icon: 'gear' },
]
</script>

<template>
  <div class="min-h-screen overflow-x-hidden bg-[var(--bg-base)] text-[var(--text-primary)]">
    <div
      v-if="isMobileMenuOpen"
      class="fixed inset-0 z-40 bg-black/45 md:hidden"
      aria-hidden="true"
      @click="isMobileMenuOpen = false"
    />

    <aside
      class="mobile-panel-pad fixed left-0 top-0 z-50 h-full w-[min(85vw,18rem)] border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-xl transition-transform duration-200 md:hidden"
      :class="isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'"
      role="dialog"
      aria-modal="true"
      aria-label="Mobile navigation menu"
    >
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Navigation</h2>
        <button
          class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm"
          aria-label="Close navigation menu"
          @click="isMobileMenuOpen = false"
        >
          Close
        </button>
      </div>
      <nav class="flex flex-col gap-2">
        <RouterLink
          v-for="item in navItems"
          :key="`mobile-${item.to}`"
          :to="item.to"
          class="flex items-center gap-2 rounded px-3 py-2 text-sm"
          :class="route.path === item.to ? 'bg-[var(--accent-info)] text-white' : 'bg-[var(--bg-elevated)]'"
        >
          <FontAwesomeIcon :icon="['fas', item.icon]" class="text-xs" />
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <header class="sticky top-0 z-20 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      <div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
        <button
          class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm md:hidden"
          aria-label="Open navigation menu"
          @click="isMobileMenuOpen = true"
        >
          Menu
        </button>
        <div class="mr-auto">
          <h1 class="flex items-center gap-2 text-lg font-semibold">
            <FontAwesomeIcon :icon="['fas', 'bolt']" class="text-sm text-[var(--accent-warning)]" />
            Moschops Operator Console
          </h1>
          <p class="text-xs text-[var(--text-secondary)]">Risk-first monitoring and training control center</p>
        </div>

        <span class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-xs font-semibold">
          Role: {{ ui.operatorRole }}
        </span>
        <select v-model="ui.environment" class="w-24 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm" aria-label="Environment selector">
          <option value="dev">dev</option>
          <option value="demo">demo</option>
          <option value="pilot">pilot</option>
          <option value="live">live</option>
        </select>

        <select v-model="ui.operatorRole" class="w-28 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm" aria-label="Operator role selector">
          <option value="viewer">viewer</option>
          <option value="analyst">analyst</option>
          <option value="admin">admin</option>
        </select>

        <select v-model="ui.strategy" class="w-40 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm" aria-label="Strategy selector">
          <option value="daily-breakout-5-10">breakout-5-10</option>
          <option value="mean-revert-eur">mean-revert-eur</option>
          <option value="macro-momentum">macro-momentum</option>
        </select>

        <select v-model="ui.datasetProfile" class="w-36 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm" aria-label="Dataset profile selector">
          <option value="rolling-90d">rolling-90d</option>
          <option value="rolling-180d">rolling-180d</option>
          <option value="event-focused">event-focused</option>
        </select>

        <input v-model="ui.startDate" type="date" class="w-36 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm" aria-label="Start date" />
        <input v-model="ui.endDate" type="date" class="w-36 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm" aria-label="End date" />

        <button class="w-[7.5rem] rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-1 text-center text-sm" @click="ui.toggleTheme()">
          <FontAwesomeIcon :icon="['fas', ui.theme === 'dark' ? 'moon' : 'sun']" class="mr-1" />
          {{ ui.theme }}
        </button>
      </div>
      <nav class="mx-auto hidden max-w-7xl gap-2 overflow-auto px-4 pb-3 md:flex">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-2 rounded px-3 py-2 text-sm whitespace-nowrap"
          :class="route.path === item.to ? 'bg-[var(--accent-info)] text-white' : 'bg-[var(--bg-elevated)]'"
        >
          <FontAwesomeIcon :icon="['fas', item.icon]" class="text-xs" />
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="mx-auto grid max-w-7xl gap-3 px-4 pb-3">
        <KillSwitchBanner
          state="normal"
          source="risk-engine"
          reason="Fail-closed posture active; protective exits remain enabled"
          timestamp="2026-05-22T14:25:00Z"
        />
        <AlertRail :alerts="alertItems" />
      </div>
    </header>
    <main class="mx-auto max-w-7xl p-4">
      <RouterView />
    </main>
  </div>
</template>
