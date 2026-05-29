<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiGet } from '../api'
import PageHeader from '../components/PageHeader.vue'
import HealthTile from '../components/HealthTile.vue'

const POLL_INTERVAL_MS = 10_000
const STALE_AFTER_MS = POLL_INTERVAL_MS * 2
const WARNING_AFTER_MS = POLL_INTERVAL_MS * 3

type HealthResponse = {
  status: string
  timestamp: string
  telemetry: {
    backend: string
    database: string
    modelLoader: string
    modelReason: string | null
    newsProvider: {
      provider: string
      tier: string
      freshnessState: string
      lastAttemptedSyncUtc: string | null
      lastSuccessfulSyncUtc: string | null
      failureReason: string | null
      budgetUsed: number | null
      budgetLimit: number | null
    }
  }
}

const loading = ref(true)
const error = ref('')
const health = ref<HealthResponse | null>(null)
const inFlight = ref(false)
const nowMs = ref(Date.now())
const lastUpdatedUtc = ref<string | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null

const viewFreshness = computed(() => {
  if (!lastUpdatedUtc.value) {
    return { label: 'UNAVAILABLE', toneClass: 'text-[var(--accent-warning)]' }
  }

  const ageMs = nowMs.value - Date.parse(lastUpdatedUtc.value)

  if (ageMs >= WARNING_AFTER_MS) {
    return { label: 'STALE_WARNING', toneClass: 'text-[var(--accent-danger)]' }
  }

  if (ageMs >= STALE_AFTER_MS) {
    return { label: 'STALE', toneClass: 'text-[var(--accent-warning)]' }
  }

  return { label: 'FRESH', toneClass: 'text-[var(--accent-success)]' }
})

function mapSeverity(status: string): 'success' | 'warning' | 'critical' | 'info' {
  const normalized = status.toUpperCase()

  if (normalized === 'UP' || normalized === 'FRESH') {
    return 'success'
  }

  if (normalized === 'DEGRADED' || normalized === 'STALE') {
    return 'warning'
  }

  if (normalized === 'DOWN') {
    return 'critical'
  }

  return 'info'
}

async function loadHealth() {
  if (inFlight.value) {
    return
  }

  inFlight.value = true
  loading.value = lastUpdatedUtc.value === null
  error.value = ''

  try {
    health.value = await apiGet<HealthResponse>('/health')
    lastUpdatedUtc.value = new Date().toISOString()
  } catch (e) {
    error.value = `N/A: ${(e as Error).message}`
  } finally {
    inFlight.value = false
    loading.value = false
  }
}

onMounted(() => {
  void loadHealth()
  pollTimer = setInterval(() => {
    void loadHealth()
  }, POLL_INTERVAL_MS)
  clockTimer = setInterval(() => {
    nowMs.value = Date.now()
  }, 1_000)
})

onBeforeUnmount(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
  if (clockTimer) {
    clearInterval(clockTimer)
  }
})
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="heartbeat" title="System Health" subtitle="Backend, DB, model loader, and provider telemetry with freshness visibility" />

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <h2 class="text-sm font-semibold">System Health Snapshot</h2>
        <div class="min-w-[18rem] text-right text-xs">
          <p class="text-[var(--text-secondary)]">Last updated (UTC): {{ lastUpdatedUtc ?? 'N/A' }}</p>
          <p class="font-semibold" :class="viewFreshness.toneClass">Panel freshness: {{ viewFreshness.label }}</p>
        </div>
      </div>
      <p v-if="loading" class="mt-2 text-sm text-[var(--text-secondary)]">Loading...</p>
      <p v-else-if="error" class="mt-2 text-sm text-[var(--accent-danger)]">{{ error }}</p>
    </section>

    <div class="grid gap-4 lg:grid-cols-4">
      <HealthTile
        label="Backend"
        :status="health?.telemetry.backend?.toUpperCase() ?? 'N/A'"
        :severity="mapSeverity(health?.telemetry.backend ?? 'N/A')"
        source="backend"
        :timestamp="lastUpdatedUtc ?? ''"
        details="API process availability and request handling status."
      />

      <HealthTile
        label="Database"
        :status="health?.telemetry.database?.toUpperCase() ?? 'N/A'"
        :severity="mapSeverity(health?.telemetry.database ?? 'N/A')"
        source="database"
        :timestamp="lastUpdatedUtc ?? ''"
        details="PostgreSQL connectivity and query response status."
      />

      <HealthTile
        label="Model Loader"
        :status="health?.telemetry.modelLoader?.toUpperCase() ?? 'N/A'"
        :severity="mapSeverity(health?.telemetry.modelLoader ?? 'N/A')"
        source="model-loader"
        :timestamp="lastUpdatedUtc ?? ''"
        :details="health?.telemetry.modelReason ?? 'No current model loading issue.'"
      />

      <HealthTile
        label="News Provider"
        :status="health?.telemetry.newsProvider.freshnessState ?? 'N/A'"
        :severity="mapSeverity(health?.telemetry.newsProvider.freshnessState ?? 'N/A')"
        source="news-provider"
        :timestamp="health?.telemetry.newsProvider.lastSuccessfulSyncUtc ?? ''"
        :details="`${health?.telemetry.newsProvider.provider ?? 'N/A'} (${health?.telemetry.newsProvider.tier ?? 'N/A'}) | Budget ${health?.telemetry.newsProvider.budgetUsed ?? 0} / ${health?.telemetry.newsProvider.budgetLimit ?? 'N/A'}`"
      />
    </div>
  </div>
</template>
