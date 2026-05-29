<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useUiStore } from './stores/ui'
import { apiGet } from './api'
import KillSwitchBanner from './components/KillSwitchBanner.vue'
import AlertRail from './components/AlertRail.vue'
import IconActionButton from './components/IconActionButton.vue'
import IconLabel from './components/IconLabel.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import EnvironmentSwitcher from './components/EnvironmentSwitcher.vue'
import StrategyFilter from './components/StrategyFilter.vue'
import DateRangePicker from './components/DateRangePicker.vue'

const ui = useUiStore()
const route = useRoute()
const isMobileMenuOpen = ref(false)
const providerName = ref('N/A')
const providerTier = ref('N/A')
const providerFreshness = ref('UNAVAILABLE')
const providerLastSuccess = ref<string | null>(null)
const killSwitchState = ref<'normal' | 'armed' | 'tripped'>('normal')
const killSwitchReason = ref('No active override')
const killSwitchTimestamp = ref('')
const alertItems = ref<
  Array<{
    id: string
    severity: 'info' | 'warning' | 'critical' | 'success'
    title: string
    detail: string
    source: string
    timestamp: string
  }>
>([])

const strategyOptions = ['daily-breakout-5-10', 'mean-revert-eur', 'macro-momentum']

type HeaderHealthResponse = {
  status: string
  timestamp: string
  telemetry: {
    database: string
    newsProvider: {
      provider: string
      tier: string
      freshnessState: string
      lastSuccessfulSyncUtc: string | null
      failureReason: string | null
    }
  }
}

type IncidentResponse = {
  items: Array<{
    incidentId: string
    severity: string
    summary: string
    eventType: string
    createdAtUtc: string
  }>
}

let providerPollTimer: ReturnType<typeof setInterval> | null = null

const onKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    isMobileMenuOpen.value = false
  }
}

const providerToneClass = computed(() => {
  if (providerFreshness.value === 'FRESH') {
    return 'text-[var(--accent-success)]'
  }

  if (providerFreshness.value === 'DEGRADED' || providerFreshness.value === 'STALE') {
    return 'text-[var(--accent-warning)]'
  }

  if (providerFreshness.value === 'DOWN') {
    return 'text-[var(--accent-danger)]'
  }

  return 'text-[var(--text-primary)]'
})

const providerSubtitle = computed(() => {
  if (!providerLastSuccess.value) {
    return `Freshness ${providerFreshness.value} | No successful sync yet`
  }

  return `Freshness ${providerFreshness.value} | Last success ${providerLastSuccess.value}`
})

function mapSeverity(value: string): 'info' | 'warning' | 'critical' | 'success' {
  const normalized = value.toUpperCase()

  if (normalized === 'CRITICAL' || normalized === 'ERROR' || normalized === 'DOWN') {
    return 'critical'
  }

  if (normalized === 'WARNING' || normalized === 'DEGRADED' || normalized === 'STALE') {
    return 'warning'
  }

  if (normalized === 'SUCCESS' || normalized === 'UP' || normalized === 'FRESH') {
    return 'success'
  }

  return 'info'
}

function mapKillSwitchState(database: string, freshness: string): 'normal' | 'armed' | 'tripped' {
  const db = database.toUpperCase()
  const provider = freshness.toUpperCase()

  if (db === 'DOWN' || provider === 'DOWN') {
    return 'tripped'
  }

  if (provider === 'DEGRADED' || provider === 'STALE') {
    return 'armed'
  }

  return 'normal'
}

async function loadHeaderTelemetry() {
  const [healthResult, incidentsResult] = await Promise.all([
    apiGet<HeaderHealthResponse>('/health')
      .then((value) => ({ ok: true as const, value }))
      .catch((error) => ({ ok: false as const, error })),
    apiGet<IncidentResponse>('/incidents?limit=2')
      .then((value) => ({ ok: true as const, value }))
      .catch((error) => ({ ok: false as const, error })),
  ])

  if (healthResult.ok) {
    const response = healthResult.value
    providerName.value = response.telemetry.newsProvider.provider
    providerTier.value = response.telemetry.newsProvider.tier
    providerFreshness.value = response.telemetry.newsProvider.freshnessState
    providerLastSuccess.value = response.telemetry.newsProvider.lastSuccessfulSyncUtc

    killSwitchState.value = mapKillSwitchState(
      response.telemetry.database,
      response.telemetry.newsProvider.freshnessState,
    )
    killSwitchTimestamp.value = response.timestamp
    killSwitchReason.value =
      response.telemetry.newsProvider.failureReason ??
      (killSwitchState.value === 'normal'
        ? 'Fail-closed posture active; protective exits remain enabled'
        : 'Safety posture raised due to dependency freshness degradation')
  } else {
    providerFreshness.value = 'UNAVAILABLE'
    providerLastSuccess.value = null
    killSwitchState.value = 'armed'
    killSwitchReason.value = 'Backend health unavailable; assume guarded posture until recovered'
    killSwitchTimestamp.value = new Date().toISOString()
  }

  if (incidentsResult.ok) {
    alertItems.value = incidentsResult.value.items.map((incident) => ({
      id: incident.incidentId,
      severity: mapSeverity(incident.severity),
      title: incident.eventType,
      detail: incident.summary,
      source: 'incidents',
      timestamp: incident.createdAtUtc,
    }))
  } else {
    alertItems.value = []
  }
}

onMounted(() => {
  ui.applyTheme()
  window.addEventListener('keydown', onKeyDown)
  void loadHeaderTelemetry()
  providerPollTimer = setInterval(() => {
    void loadHeaderTelemetry()
  }, 30_000)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  if (providerPollTimer) {
    clearInterval(providerPollTimer)
  }
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
    <a href="#main-content" class="skip-link">Skip to main content</a>

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
        <IconActionButton icon="circle-xmark" label="Close" aria-label="Close navigation menu" @click="isMobileMenuOpen = false" />
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
        <IconActionButton icon="list-check" label="Menu" aria-label="Open navigation menu" class="md:hidden" @click="isMobileMenuOpen = true" />
        <div class="mr-auto">
          <h1 class="flex items-center gap-2 text-lg font-semibold">
            <FontAwesomeIcon :icon="['fas', 'bolt']" class="text-sm text-[var(--accent-warning)]" />
            Moschops Operator Console
          </h1>
          <p class="text-xs text-[var(--text-secondary)]">Risk-first monitoring and training control center</p>
        </div>

        <IconLabel icon="user-shield" :label="`Role ${ui.operatorRole}`" />
        <IconLabel icon="heartbeat" :label="`News ${providerName} (${providerTier})`" :subtitle="providerSubtitle" :tone-class="providerToneClass" />
        <EnvironmentSwitcher v-model="ui.environment" />

        <select v-model="ui.operatorRole" class="w-28 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm" aria-label="Operator role selector">
          <option value="viewer">viewer</option>
          <option value="analyst">analyst</option>
          <option value="admin">admin</option>
        </select>

        <StrategyFilter v-model="ui.strategy" :options="strategyOptions" />

        <select v-model="ui.datasetProfile" class="w-36 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm" aria-label="Dataset profile selector">
          <option value="rolling-90d">rolling-90d</option>
          <option value="rolling-180d">rolling-180d</option>
          <option value="event-focused">event-focused</option>
        </select>

        <DateRangePicker
          :start-date="ui.startDate"
          :end-date="ui.endDate"
          @update:startDate="ui.startDate = $event"
          @update:endDate="ui.endDate = $event"
        />

        <ThemeToggle :theme="ui.theme" @toggle="ui.toggleTheme()" />
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
          :state="killSwitchState"
          source="risk-engine"
          :reason="killSwitchReason"
          :timestamp="killSwitchTimestamp"
        />
        <AlertRail v-if="alertItems.length > 0" :alerts="alertItems" />
      </div>
    </header>
    <main id="main-content" class="mx-auto max-w-7xl p-4">
      <RouterView />
    </main>
  </div>
</template>
