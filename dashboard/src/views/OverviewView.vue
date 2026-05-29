<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiGet } from '../api'
import PageHeader from '../components/PageHeader.vue'
import VChart from 'vue-echarts'
import MetricCard from '../components/MetricCard.vue'
import DeltaPill from '../components/DeltaPill.vue'
import DataPanel from '../components/DataPanel.vue'

const POLL_INTERVAL_MS = 30_000
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
      lastSuccessfulSyncUtc: string | null
      failureReason: string | null
    }
  }
}

type ModelVersionResponse = {
  strategyId: string
  strategyVersion: string
  modelVersion: string
  lifecycleState: string
  createdAt: string
}

type PerformanceSnapshot = {
  id: string
  modelVersion: string | null
  expectancy: number | null
  sharpe: number | null
  maxDrawdown: number | null
  tradeCount: number | null
  snapshotJson: Record<string, unknown>
  capturedAtUtc: string
}

type TrainingRun = {
  trainingRunId: string
  status: string
  createdAt: string
}

type IncidentItem = {
  incidentId: string
  severity: string
  summary: string
  runbookId: string
  createdAtUtc: string
  acknowledged: boolean
}

const loading = ref(true)
const error = ref('')
const partialErrors = ref<string[]>([])
const updatedAt = ref('')
const nowMs = ref(Date.now())

const health = ref<HealthResponse | null>(null)
const model = ref<ModelVersionResponse | null>(null)
const performance = ref<PerformanceSnapshot[]>([])
const trainingRuns = ref<TrainingRun[]>([])
const incidents = ref<IncidentItem[]>([])

let pollTimer: ReturnType<typeof setInterval> | null = null
let clockTimer: ReturnType<typeof setInterval> | null = null

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function extractEquity(snapshot: PerformanceSnapshot): number | null {
  const json = snapshot.snapshotJson

  const candidates = [
    asNumber(json.equity),
    asNumber(json.equityValue),
    asNumber(json.balance),
    asNumber(json.netEquity),
    asNumber(snapshot.tradeCount),
  ]

  return candidates.find((value) => value !== null) ?? null
}

function formatNumber(value: number | null, digits = 2): string {
  if (value === null) {
    return 'N/A'
  }

  return value.toFixed(digits)
}

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

const equityOption = computed(() => {
  const sorted = [...performance.value].sort((a, b) => Date.parse(a.capturedAtUtc) - Date.parse(b.capturedAtUtc))
  const labels = sorted.map((item) => item.capturedAtUtc)
  const equitySeries = sorted.map((item) => extractEquity(item))
  const drawdownSeries = sorted.map((item) => item.maxDrawdown ?? null)

  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 4, textStyle: { color: 'var(--text-secondary)' } },
    grid: { left: 32, right: 22, top: 42, bottom: 30 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        formatter: (value: string) => value.slice(5, 16).replace('T', ' '),
      },
    },
    yAxis: [{ type: 'value' }, { type: 'value' }],
    series: [
      {
        name: 'Equity proxy',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        data: equitySeries,
        areaStyle: {},
      },
      {
        name: 'Max drawdown',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: drawdownSeries,
      },
    ],
  }
})

const keyMetrics = computed(() => {
  const dbStatus = health.value?.telemetry.database?.toUpperCase() ?? 'UNKNOWN'
  const providerFreshness = health.value?.telemetry.newsProvider?.freshnessState?.toUpperCase() ?? 'UNKNOWN'
  const modelVersion = model.value?.modelVersion ?? 'N/A'

  let globalRiskState = 'Normal'
  if (dbStatus !== 'UP' || providerFreshness === 'DOWN') {
    globalRiskState = 'Guarded'
  }
  if (providerFreshness === 'STALE' || providerFreshness === 'DEGRADED') {
    globalRiskState = 'Elevated'
  }

  const runningCount = trainingRuns.value.filter((item) => item.status === 'RUNNING').length
  const pendingCount = trainingRuns.value.filter((item) => item.status === 'PENDING').length
  const queueText = `${runningCount} running / ${pendingCount} pending`

  return [
    {
      label: 'Global Risk State',
      value: globalRiskState,
      subtitle: `DB ${dbStatus} | News ${providerFreshness}`,
    },
    {
      label: 'Active Strategy',
      value: model.value?.strategyId ?? 'N/A',
      subtitle: `Version ${model.value?.strategyVersion ?? 'N/A'}`,
    },
    {
      label: 'Latest Model',
      value: modelVersion,
      subtitle: `Lifecycle ${model.value?.lifecycleState ?? 'UNKNOWN'}`,
    },
    {
      label: 'Training Queue',
      value: queueText,
      subtitle: trainingRuns.value[0]?.createdAt ?? 'No recent training run',
    },
  ]
})

const keyDeltas = computed(() => {
  if (performance.value.length < 2) {
    return [] as Array<{ label: string; value: number }>
  }

  const sorted = [...performance.value].sort((a, b) => Date.parse(b.capturedAtUtc) - Date.parse(a.capturedAtUtc))
  const latest = sorted[0]
  const previous = sorted[1]

  return [
    {
      label: 'Expectancy delta',
      value: (latest.expectancy ?? 0) - (previous.expectancy ?? 0),
    },
    {
      label: 'Sharpe delta',
      value: (latest.sharpe ?? 0) - (previous.sharpe ?? 0),
    },
    {
      label: 'Drawdown delta',
      value: (latest.maxDrawdown ?? 0) - (previous.maxDrawdown ?? 0),
    },
  ]
})

const latestPerformance = computed(() => {
  if (performance.value.length === 0) {
    return null
  }

  return [...performance.value].sort((a, b) => Date.parse(b.capturedAtUtc) - Date.parse(a.capturedAtUtc))[0]
})

async function loadOverviewData() {
  loading.value = true
  error.value = ''

  const results = await Promise.all([
    apiGet<HealthResponse>('/health')
      .then((value) => ({ ok: true as const, value }))
      .catch((error) => ({ ok: false as const, error })),
    apiGet<ModelVersionResponse>('/model-version')
      .then((value) => ({ ok: true as const, value }))
      .catch((error) => ({ ok: false as const, error })),
    apiGet<{ count: number; items: PerformanceSnapshot[] }>('/performance')
      .then((value) => ({ ok: true as const, value }))
      .catch((error) => ({ ok: false as const, error })),
    apiGet<{ count: number; items: TrainingRun[] }>('/training/runs?limit=20')
      .then((value) => ({ ok: true as const, value }))
      .catch((error) => ({ ok: false as const, error })),
    apiGet<{ count: number; items: IncidentItem[] }>('/incidents?limit=8')
      .then((value) => ({ ok: true as const, value }))
      .catch((error) => ({ ok: false as const, error })),
  ])

  const [healthRes, modelRes, performanceRes, trainingRes, incidentsRes] = results
  const errors: string[] = []

  if (healthRes.ok) {
    health.value = healthRes.value
  } else {
    errors.push(`health: ${'error' in healthRes && healthRes.error instanceof Error ? healthRes.error.message : 'failed'}`)
  }

  if (modelRes.ok) {
    model.value = modelRes.value
  } else {
    errors.push(`model-version: ${'error' in modelRes && modelRes.error instanceof Error ? modelRes.error.message : 'failed'}`)
  }

  if (performanceRes.ok) {
    performance.value = performanceRes.value.items
  } else {
    errors.push(`performance: ${'error' in performanceRes && performanceRes.error instanceof Error ? performanceRes.error.message : 'failed'}`)
  }

  if (trainingRes.ok) {
    trainingRuns.value = trainingRes.value.items
  } else {
    errors.push(`training: ${'error' in trainingRes && trainingRes.error instanceof Error ? trainingRes.error.message : 'failed'}`)
  }

  if (incidentsRes.ok) {
    incidents.value = incidentsRes.value.items
  } else {
    errors.push(`incidents: ${'error' in incidentsRes && incidentsRes.error instanceof Error ? incidentsRes.error.message : 'failed'}`)
  }

  partialErrors.value = errors

  if (errors.length === 5) {
    error.value = 'All overview data providers failed. Verify backend connectivity and retry.'
  }

  updatedAt.value = new Date().toISOString()
  loading.value = false
}

onMounted(() => {
  void loadOverviewData()
  pollTimer = setInterval(() => {
    void loadOverviewData()
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
    <PageHeader icon="gauge-high" title="Overview" subtitle="Risk-first control surface with training and health at a glance" />

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="flex flex-wrap items-start justify-between gap-2">
        <h2 class="text-sm font-semibold">Overview Freshness</h2>
        <div class="min-w-[18rem] text-right text-xs">
          <p class="text-[var(--text-secondary)]">Last updated (UTC): {{ updatedAt || 'N/A' }}</p>
          <p class="font-semibold" :class="panelFreshness.toneClass">Panel freshness: {{ panelFreshness.label }}</p>
        </div>
      </div>
      <p v-if="error" class="mt-2 text-sm text-[var(--accent-danger)]">{{ error }}</p>
      <ul v-else-if="partialErrors.length > 0" class="mt-2 list-disc pl-5 text-xs text-[var(--accent-warning)]">
        <li v-for="item in partialErrors" :key="item">Partial data unavailable: {{ item }}</li>
      </ul>
      <button class="mt-3 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-1.5 text-sm" @click="loadOverviewData">
        Retry data load
      </button>
    </section>

    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        v-for="metric in keyMetrics"
        :key="metric.label"
        :label="metric.label"
        :value="metric.value"
        :subtitle="metric.subtitle"
      />
    </div>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="mb-2 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Session Delta Snapshot</h2>
        <p class="text-xs text-[var(--text-secondary)]">Compared with prior persisted performance snapshot</p>
      </div>
      <div v-if="keyDeltas.length === 0" class="text-sm text-[var(--text-secondary)]">Not enough performance snapshots for delta analysis.</div>
      <div v-else class="flex flex-wrap gap-2">
        <DeltaPill v-for="delta in keyDeltas" :key="delta.label" :label="delta.label" :value="delta.value" />
      </div>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Equity and Drawdown Trend</h2>
        <p class="text-xs text-[var(--text-secondary)]">
          Latest expectancy {{ formatNumber(latestPerformance?.expectancy ?? null, 3) }} | Sharpe {{ formatNumber(latestPerformance?.sharpe ?? null, 3) }}
        </p>
      </div>
      <div class="h-64 overflow-hidden">
        <VChart :option="equityOption" autoresize class="h-full w-full" />
      </div>
    </section>

    <DataPanel title="Active Incidents" :loading="loading" :error="error" :updated-at="updatedAt">
      <ul v-if="incidents.length > 0" class="space-y-2 text-sm">
        <li v-for="item in incidents" :key="item.incidentId" class="rounded border border-[var(--border-subtle)] p-3">
          <div class="flex flex-wrap items-center gap-2">
            <p class="font-semibold">{{ item.incidentId }}</p>
            <span class="rounded bg-[var(--bg-elevated)] px-2 py-0.5 text-xs">{{ item.severity.toUpperCase() }}</span>
            <span class="text-xs text-[var(--text-secondary)]">{{ item.createdAtUtc }}</span>
            <span v-if="item.acknowledged" class="rounded bg-[var(--bg-elevated)] px-2 py-0.5 text-xs">Acknowledged</span>
          </div>
          <p class="mt-1 text-[var(--text-secondary)]">{{ item.summary }}</p>
          <p class="mt-1 text-xs text-[var(--text-secondary)]">Runbook: {{ item.runbookId }}</p>
        </li>
      </ul>
      <p v-else class="text-sm text-[var(--text-secondary)]">No incident events are currently recorded.</p>
    </DataPanel>

    <DataPanel title="System Health" :loading="loading" :error="error" :updated-at="updatedAt">
      <p class="text-sm">Backend status: {{ health?.status ?? 'N/A' }}</p>
      <p class="text-xs text-[var(--text-secondary)]">Model loader: {{ health?.telemetry.modelLoader ?? 'N/A' }}</p>
      <p class="text-xs text-[var(--text-secondary)]">
        Provider freshness: {{ health?.telemetry.newsProvider.freshnessState ?? 'N/A' }}
      </p>
    </DataPanel>
  </div>
</template>
