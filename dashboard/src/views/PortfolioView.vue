<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import { apiGet } from '../api'
import PlotlyPanel from '../components/PlotlyPanel.vue'

const POLL_INTERVAL_MS = 20_000
const STALE_AFTER_MS = POLL_INTERVAL_MS * 2
const WARNING_AFTER_MS = POLL_INTERVAL_MS * 3

type ExposureItem = {
  symbol: string
  count: number
  sharePct: number
  assetClass: string
}

type VetoItem = {
  reasonCode: string
  count: number
}

type PortfolioSummaryResponse = {
  generatedAtUtc: string
  sourceDecisionId: string | null
  exposureBySymbol: ExposureItem[]
  openRiskBudget: {
    maxOpenRisk: number
    remainingRiskBudget: number
    consumedRiskBudget: number
    consumedPct: number
  }
  tradeSlots: {
    maxOpenTrades: number
    remainingTradeSlots: number
    consumedTradeSlots: number
    consumedPct: number
  }
  vetoBreakdownTop: VetoItem[]
  correlationConcentration: {
    flaggedCount: number
    totalRejected: number
    ratioPct: number
  }
}

const loading = ref(true)
const error = ref('')
const summary = ref<PortfolioSummaryResponse | null>(null)
const updatedAt = ref('')
const nowMs = ref(Date.now())

let pollTimer: ReturnType<typeof setInterval> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null

const panelFreshness = computed(() => {
  if (!updatedAt.value) {
    return { label: 'UNAVAILABLE', toneClass: 'text-[var(--accent-warning)]' }
  }

  const ageMs = nowMs.value - Date.parse(updatedAt.value)

  if (ageMs >= WARNING_AFTER_MS) {
    return { label: 'STALE_WARNING', toneClass: 'text-[var(--accent-danger)]' }
  }

  if (ageMs >= STALE_AFTER_MS) {
    return { label: 'STALE', toneClass: 'text-[var(--accent-warning)]' }
  }

  return { label: 'FRESH', toneClass: 'text-[var(--accent-success)]' }
})

const exposurePlotData = computed(() => {
  const items = summary.value?.exposureBySymbol ?? []
  if (items.length === 0) {
    return [] as unknown[]
  }

  return [
    {
      type: 'pie',
      hole: 0.5,
      labels: items.map((item) => `${item.symbol} (${item.assetClass})`),
      values: items.map((item) => item.count),
      texttemplate: '%{label}<br>%{percent}',
      hovertemplate: '<b>%{label}</b><br>Rows %{value}<extra></extra>',
    },
  ]
})

const budgetPlotData = computed(() => {
  const risk = summary.value?.openRiskBudget
  const slots = summary.value?.tradeSlots

  if (!risk || !slots) {
    return [] as unknown[]
  }

  return [
    {
      type: 'bar',
      orientation: 'h',
      name: 'Consumed',
      x: [risk.consumedPct, slots.consumedPct],
      y: ['Open risk budget', 'Trade slots'],
      marker: { color: '#dc6803' },
    },
    {
      type: 'bar',
      orientation: 'h',
      name: 'Remaining',
      x: [Math.max(0, 100 - risk.consumedPct), Math.max(0, 100 - slots.consumedPct)],
      y: ['Open risk budget', 'Trade slots'],
      marker: { color: '#039855' },
    },
  ]
})

const budgetPlotLayout = {
  barmode: 'stack',
  margin: { l: 120, r: 12, t: 12, b: 30 },
  xaxis: {
    title: { text: 'Percent consumed' },
    range: [0, 100],
  },
}

const topVetoReasons = computed(() => (summary.value?.vetoBreakdownTop ?? []).slice(0, 5))

async function loadPortfolioSummary() {
  loading.value = true
  error.value = ''

  try {
    summary.value = await apiGet<PortfolioSummaryResponse>('/portfolio/summary?maxOpenRisk=0.04&maxOpenTrades=6&lookback=200')
    updatedAt.value = new Date().toISOString()
  } catch (e) {
    error.value = `N/A: ${(e as Error).message}`
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadPortfolioSummary()
  pollTimer = setInterval(() => {
    void loadPortfolioSummary()
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
    <PageHeader icon="briefcase" title="Portfolio" subtitle="Exposure concentration, budget posture, and correlation concentration from live data" />

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <h2 class="text-sm font-semibold">Portfolio Summary Freshness</h2>
        <div class="min-w-[18rem] text-right text-xs">
          <p class="text-[var(--text-secondary)]">Last updated (UTC): {{ updatedAt || 'N/A' }}</p>
          <p class="font-semibold" :class="panelFreshness.toneClass">Panel freshness: {{ panelFreshness.label }}</p>
        </div>
      </div>
      <p v-if="error" class="mt-2 text-sm text-[var(--accent-danger)]">{{ error }}</p>
      <button class="mt-3 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-1.5 text-sm" @click="loadPortfolioSummary">
        Retry summary load
      </button>
    </section>

    <div class="grid gap-4 lg:grid-cols-2">
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Exposure by Symbol and Asset Class</h2>
        <PlotlyPanel
          :data="exposurePlotData"
          :loading="loading"
          :error="error"
          empty-message="No open exposure records available yet."
          height-class="h-72"
        />
      </section>

      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Risk Budget and Trade Slot Consumption</h2>
        <PlotlyPanel
          :data="budgetPlotData"
          :layout="budgetPlotLayout"
          :loading="loading"
          :error="error"
          empty-message="No budget source data available yet."
          height-class="h-72"
        />
      </section>
    </div>

    <div class="grid gap-4 lg:grid-cols-2">
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Correlation Concentration Indicators</h2>
        <p class="text-sm">
          Correlation-related veto ratio:
          <span class="font-semibold">{{ summary?.correlationConcentration.ratioPct.toFixed(2) ?? '0.00' }}%</span>
        </p>
        <p class="text-xs text-[var(--text-secondary)]">
          {{ summary?.correlationConcentration.flaggedCount ?? 0 }} flagged events across {{ summary?.correlationConcentration.totalRejected ?? 0 }} rejected decisions.
        </p>
      </section>

      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Top Veto Drivers</h2>
        <ul v-if="topVetoReasons.length > 0" class="space-y-2 text-sm">
          <li v-for="item in topVetoReasons" :key="item.reasonCode" class="rounded border border-[var(--border-subtle)] p-2">
            <p class="font-semibold">{{ item.reasonCode }}</p>
            <p class="text-xs text-[var(--text-secondary)]">Count: {{ item.count }}</p>
          </li>
        </ul>
        <p v-else class="text-sm text-[var(--text-secondary)]">No veto reasons recorded in the selected lookback window.</p>
      </section>
    </div>
  </div>
</template>
