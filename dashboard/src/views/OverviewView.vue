<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiGet } from '../api'
import PageHeader from '../components/PageHeader.vue'
import VChart from 'vue-echarts'

type HealthResponse = { status: string; timestamp: string }

const health = ref<HealthResponse | null>(null)
const error = ref('')
const loading = ref(true)

const equityOption = {
  tooltip: { trigger: 'axis' },
  grid: { left: 32, right: 18, top: 20, bottom: 26 },
  xAxis: {
    type: 'category',
    data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
  },
  yAxis: { type: 'value' },
  series: [
    {
      type: 'line',
      smooth: true,
      data: [100, 103, 101, 106, 108],
      areaStyle: {},
    },
  ],
}

const incidents = [
  { id: 'INC-2201', severity: 'warning', text: 'Provider historical entitlement constrained' },
  { id: 'INC-2202', severity: 'info', text: 'Training queue idle and ready for launch' },
]

async function fetchHealth() {
  loading.value = true
  error.value = ''
  try {
    health.value = await apiGet<HealthResponse>('/health')
  } catch (e) {
    error.value = `N/A: ${(e as Error).message}`
  } finally {
    loading.value = false
  }
}

onMounted(fetchHealth)
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="gauge-high" title="Overview" subtitle="Risk-first control surface with training and health at a glance" />

    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Global Risk State</p>
        <p class="mt-1 text-xl font-semibold">Guarded</p>
      </section>
      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Active Strategy</p>
        <p class="mt-1 text-xl font-semibold">daily-breakout-5-10</p>
      </section>
      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Latest Model</p>
        <p class="mt-1 text-xl font-semibold">logreg-2026-05-20</p>
      </section>
      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Training Queue</p>
        <p class="mt-1 text-xl font-semibold">2 pending</p>
      </section>
    </div>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <h2 class="text-sm font-semibold">Temporarily Disabled</h2>
      <p class="mt-2 text-sm text-[var(--text-secondary)]">Account performance and AI drift widgets are disabled until their data feeds are live.</p>
    </section>
    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Equity and Drawdown Snapshot</h2>
        <p class="text-xs text-[var(--text-secondary)]">UTC week view</p>
      </div>
      <div class="h-64 overflow-hidden">
        <VChart :option="equityOption" autoresize class="h-full w-full" />
      </div>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h2 class="mb-2 text-sm font-semibold">Active Incidents</h2>
      <ul class="space-y-2 text-sm">
        <li v-for="item in incidents" :key="item.id" class="rounded border border-[var(--border-subtle)] p-2">
          <p class="font-semibold">{{ item.id }} - {{ item.severity.toUpperCase() }}</p>
          <p class="text-[var(--text-secondary)]">{{ item.text }}</p>
        </li>
      </ul>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold">System Health</h2>
        <p v-if="health?.timestamp" class="text-xs text-[var(--text-secondary)]">Updated {{ health.timestamp }}</p>
      </div>

      <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading...</p>
      <p v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</p>
      <p v-else class="text-sm">Backend status: {{ health?.status ?? 'N/A' }}</p>
    </section>
  </div>
</template>
