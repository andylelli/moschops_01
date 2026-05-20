<script setup lang="ts">
import { onMounted, ref } from 'vue'
import MetricCard from '../components/MetricCard.vue'
import DataPanel from '../components/DataPanel.vue'
import { apiGet } from '../api'

type HealthResponse = { status: string; timestamp: string }

const health = ref<HealthResponse | null>(null)
const error = ref('')
const loading = ref(true)

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
    <div class="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
      <MetricCard label="Equity" value="N/A" subtitle="Awaiting account feed" />
      <MetricCard label="Drawdown" value="N/A" subtitle="Awaiting account feed" />
      <MetricCard label="Daily PnL" value="N/A" subtitle="Awaiting account feed" />
      <MetricCard label="AI Score Drift" value="N/A" subtitle="Awaiting model feed" />
    </div>
    <DataPanel title="System Health" :loading="loading" :error="error" :updated-at="health?.timestamp">
      <p class="text-sm">Backend status: {{ health?.status ?? 'N/A' }}</p>
    </DataPanel>
  </div>
</template>
