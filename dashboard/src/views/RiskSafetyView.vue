<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiGet } from '../api'
import PageHeader from '../components/PageHeader.vue'

const POLL_INTERVAL_MS = 10_000
const STALE_AFTER_MS = POLL_INTERVAL_MS * 2
const WARNING_AFTER_MS = POLL_INTERVAL_MS * 3

type ProviderItem = {
  provider: string
  tier: string
  freshnessState: string
  lastAttemptedSyncUtc: string | null
  lastSuccessfulSyncUtc: string | null
  failureReason: string | null
  budgetUsed: number | null
  budgetLimit: number | null
}

type ProviderResponse = {
  items: ProviderItem[]
}

type ActiveWindow = {
  guardWindowId: string
  newsEventId: string
  title: string
  symbolScope: string
  currencyScope: string | null
  policyAction: string
  severity: string
  reasonCode: string
  startsAtUtc: string
  endsAtUtc: string
}

type ActiveResponse = {
  count: number
  items: ActiveWindow[]
}

type UpcomingEvent = {
  newsEventId: string
  title: string
  currencyCode: string | null
  severity: string
  scheduledAtUtc: string
  status: string
}

type UpcomingResponse = {
  count: number
  items: UpcomingEvent[]
}

const loading = ref(true)
const error = ref('')
const providers = ref<ProviderItem[]>([])
const activeWindows = ref<ActiveWindow[]>([])
const upcomingEvents = ref<UpcomingEvent[]>([])
const newsIntegrationDisabled = ref(false)
const disabledReason = ref('')
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

async function loadNewsData() {
  if (inFlight.value) {
    return
  }

  inFlight.value = true
  loading.value = lastUpdatedUtc.value === null
  error.value = ''

  try {
    const providerRes = await apiGet<ProviderResponse>('/news/providers')

    const disablingProvider = providerRes.items.find(
      (provider) =>
        provider.failureReason === 'NEWS_SYNC_DISABLED' ||
        provider.failureReason?.startsWith('PROVIDER_ACCESS_DENIED_'),
    )

    providers.value = providerRes.items

    if (disablingProvider?.failureReason) {
      newsIntegrationDisabled.value = true
      disabledReason.value = disablingProvider.failureReason
      activeWindows.value = []
      upcomingEvents.value = []
      lastUpdatedUtc.value = new Date().toISOString()
      return
    }

    newsIntegrationDisabled.value = false
    disabledReason.value = ''

    const [activeRes, upcomingRes] = await Promise.all([
      apiGet<ActiveResponse>('/news/active?limit=10'),
      apiGet<UpcomingResponse>('/news/upcoming?limit=10'),
    ])

    activeWindows.value = activeRes.items
    upcomingEvents.value = upcomingRes.items
    lastUpdatedUtc.value = new Date().toISOString()
  } catch (e) {
    error.value = `N/A: ${(e as Error).message}`
  } finally {
    inFlight.value = false
    loading.value = false
  }
}

onMounted(() => {
  void loadNewsData()
  pollTimer = setInterval(() => {
    void loadNewsData()
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
    <PageHeader icon="shield-halved" title="Risk and Safety" subtitle="Kill-switch posture, provider freshness, and guard-window visibility" />

    <div class="grid gap-4 lg:grid-cols-3">
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Kill Switch</h2>
        <p class="text-base font-semibold text-[var(--accent-success)]">NORMAL</p>
        <p class="text-xs text-[var(--text-secondary)]">Protective exits remain allowed under all policy states.</p>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Daily Risk Utilization</h2>
        <p class="text-base font-semibold">58%</p>
        <p class="text-xs text-[var(--text-secondary)]">Within configured tolerance.</p>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Veto Driver (24h)</h2>
        <p class="text-base font-semibold">NEWS_PROVIDER_STALE</p>
        <p class="text-xs text-[var(--text-secondary)]">Most frequent reason code</p>
      </section>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div class="mb-2 flex flex-wrap items-start justify-between gap-2">
        <h2 class="text-sm font-semibold">News Provider Status</h2>
        <div class="min-w-[18rem] text-right text-xs">
          <p class="text-[var(--text-secondary)]">Last updated (UTC): {{ lastUpdatedUtc ?? 'N/A' }}</p>
          <p class="font-semibold" :class="viewFreshness.toneClass">Panel freshness: {{ viewFreshness.label }}</p>
        </div>
      </div>
      <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading...</p>
      <p v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</p>
      <div v-else-if="providers.length === 0" class="text-sm text-[var(--text-secondary)]">No provider status records available.</div>
      <div v-else class="space-y-2 text-sm">
        <div v-for="provider in providers" :key="provider.provider" class="rounded border border-[var(--border-subtle)] p-2">
          <p class="font-semibold">{{ provider.provider }} ({{ provider.tier }}): {{ provider.freshnessState }}</p>
          <p class="text-[var(--text-secondary)]">Last success: {{ provider.lastSuccessfulSyncUtc ?? 'N/A' }}</p>
          <p class="text-[var(--text-secondary)]">Budget: {{ provider.budgetUsed ?? 0 }} / {{ provider.budgetLimit ?? 'N/A' }}</p>
          <p v-if="provider.failureReason" class="text-[var(--text-secondary)]">Failure reason: {{ provider.failureReason }}</p>
        </div>
      </div>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div class="mb-2 flex flex-wrap items-start justify-between gap-2">
        <h2 class="text-sm font-semibold">Active News Windows</h2>
        <div class="min-w-[18rem] text-right text-xs">
          <p class="text-[var(--text-secondary)]">Last updated (UTC): {{ lastUpdatedUtc ?? 'N/A' }}</p>
          <p class="font-semibold" :class="viewFreshness.toneClass">Panel freshness: {{ viewFreshness.label }}</p>
        </div>
      </div>
      <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading...</p>
      <p v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</p>
      <p v-else-if="newsIntegrationDisabled" class="text-sm text-[var(--text-secondary)]">Disabled due to provider state: {{ disabledReason }}</p>
      <div v-else-if="activeWindows.length === 0" class="text-sm text-[var(--text-secondary)]">No active windows.</div>
      <ul v-else class="space-y-2 text-sm">
        <li v-for="window in activeWindows" :key="window.guardWindowId" class="rounded border border-[var(--border-subtle)] p-2">
          <p class="font-semibold">{{ window.symbolScope }} - {{ window.policyAction }} ({{ window.severity }})</p>
          <p class="text-[var(--text-secondary)]">{{ window.title }}</p>
          <p class="text-[var(--text-secondary)]">{{ window.startsAtUtc }} to {{ window.endsAtUtc }}</p>
        </li>
      </ul>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 lg:col-span-2">
      <div class="mb-2 flex flex-wrap items-start justify-between gap-2">
        <h2 class="text-sm font-semibold">Upcoming Scheduled Events</h2>
        <div class="min-w-[18rem] text-right text-xs">
          <p class="text-[var(--text-secondary)]">Last updated (UTC): {{ lastUpdatedUtc ?? 'N/A' }}</p>
          <p class="font-semibold" :class="viewFreshness.toneClass">Panel freshness: {{ viewFreshness.label }}</p>
        </div>
      </div>
      <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading...</p>
      <p v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</p>
      <p v-else-if="newsIntegrationDisabled" class="text-sm text-[var(--text-secondary)]">Disabled due to provider state: {{ disabledReason }}</p>
      <div v-else-if="upcomingEvents.length === 0" class="text-sm text-[var(--text-secondary)]">No upcoming events.</div>
      <ul v-else class="grid gap-2 md:grid-cols-2">
        <li v-for="event in upcomingEvents" :key="event.newsEventId" class="rounded border border-[var(--border-subtle)] p-3 text-sm">
          <p class="font-semibold">{{ event.title }}</p>
          <p class="text-[var(--text-secondary)]">
            <span
              :title="event.currencyCode ? '' : 'Data unavailable due to missing provider field for currency code.'"
            >
              {{ event.currencyCode ?? 'N/A' }}
            </span>
            - {{ event.severity }}
          </p>
          <p class="text-[var(--text-secondary)]">{{ event.scheduledAtUtc }}</p>
        </li>
      </ul>
    </section>
    </div>
  </div>
</template>
