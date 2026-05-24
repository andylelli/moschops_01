<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiGet } from '../api'
import PageHeader from '../components/PageHeader.vue'

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
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <h3 class="mb-2 text-sm font-semibold">Backend</h3>
        <p class="text-sm">{{ health?.telemetry.backend ?? 'N/A' }}</p>
      </section>

      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <h3 class="mb-2 text-sm font-semibold">Database</h3>
        <p class="text-sm">{{ health?.telemetry.database ?? 'N/A' }}</p>
      </section>

      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <h3 class="mb-2 text-sm font-semibold">Model Loader</h3>
        <p class="text-sm">{{ health?.telemetry.modelLoader ?? 'N/A' }}</p>
        <p class="text-sm text-[var(--text-secondary)]">{{ health?.telemetry.modelReason ?? 'No current model loading issue.' }}</p>
      </section>

      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <h3 class="mb-2 text-sm font-semibold">News Provider</h3>
        <p class="text-sm font-semibold">
          {{ health?.telemetry.newsProvider.provider ?? 'N/A' }}
          <span v-if="health?.telemetry.newsProvider.tier">({{ health.telemetry.newsProvider.tier }})</span>
        </p>
        <p class="text-sm text-[var(--text-secondary)]">Freshness: {{ health?.telemetry.newsProvider.freshnessState ?? 'N/A' }}</p>
        <p class="text-sm text-[var(--text-secondary)]">Last success: {{ health?.telemetry.newsProvider.lastSuccessfulSyncUtc ?? 'N/A' }}</p>
        <p class="text-sm text-[var(--text-secondary)]">Budget: {{ health?.telemetry.newsProvider.budgetUsed ?? 0 }} / {{ health?.telemetry.newsProvider.budgetLimit ?? 'N/A' }}</p>
      </section>
    </div>
  </div>
</template>
