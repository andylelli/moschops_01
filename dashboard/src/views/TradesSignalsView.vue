<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiGet } from '../api'
import PageHeader from '../components/PageHeader.vue'
import DataPanel from '../components/DataPanel.vue'
import TradeLedgerTable, { type TradeLedgerRow } from '../components/TradeLedgerTable.vue'

type OpenTradesResponse = {
  count: number
  items: Array<{
    id: string
    symbol: string | null
    capturedAtUtc: string
    decisionId?: string | null
    signalId?: string | null
    tradeId?: string | null
    timeframe?: string | null
    modelVersion?: string | null
    status?: string | null
  }>
}

const data = ref<OpenTradesResponse | null>(null)
const loading = ref(true)
const error = ref('')
const updatedAt = ref('')

const rows = computed<TradeLedgerRow[]>(() => {
  const items = data.value?.items ?? []

  return items.map((item) => {
    const fallbackId = item.id.slice(0, 8).toUpperCase()
    return {
      id: item.id,
      decisionId: item.decisionId ?? `DEC-${fallbackId}`,
      signalId: item.signalId ?? `SIG-${fallbackId}`,
      tradeId: item.tradeId ?? `TRD-${fallbackId}`,
      symbol: item.symbol ?? 'N/A',
      timeframe: item.timeframe ?? 'D1',
      modelVersion: item.modelVersion ?? 'N/A',
      status: item.status ?? 'OPEN',
      capturedAtUtc: item.capturedAtUtc,
    }
  })
})

onMounted(async () => {
  loading.value = true
  try {
    data.value = await apiGet<OpenTradesResponse>('/trades/open')
    updatedAt.value = new Date().toISOString()
  } catch (e) {
    error.value = `N/A: ${(e as Error).message}`
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="arrow-right-arrow-left" title="Trades and Signals" subtitle="Accepted/rejected decisions, reason codes, and open trade snapshots" />

    <DataPanel title="Open Trades Snapshot" :loading="loading" :error="error" :updated-at="updatedAt">
      <p class="mb-3 text-xs text-[var(--text-secondary)]">Hydrated from GET /trades/open. Includes deterministic decision/signal/trade identifiers.</p>
      <p v-if="rows.length === 0" class="text-sm text-[var(--text-secondary)]">No open trades found for the selected filters.</p>
      <TradeLedgerTable v-else :rows="rows" />
    </DataPanel>
  </div>
</template>
