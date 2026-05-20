<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiGet } from '../api'

type OpenTradesResponse = {
  count: number
  items: Array<{ id: string; symbol: string | null; capturedAtUtc: string }>
}

const data = ref<OpenTradesResponse | null>(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  loading.value = true
  try {
    data.value = await apiGet<OpenTradesResponse>('/trades/open')
  } catch (e) {
    error.value = `N/A: ${(e as Error).message}`
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
    <h2 class="mb-2 text-sm font-semibold">Open Trades Snapshot</h2>
    <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading...</p>
    <p v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</p>
    <div v-else class="space-y-2">
      <p class="text-sm">Records: {{ data?.count ?? 0 }}</p>
      <ul class="space-y-1 text-sm text-[var(--text-secondary)]">
        <li v-for="item in data?.items ?? []" :key="item.id">{{ item.symbol ?? 'N/A' }} at {{ item.capturedAtUtc }}</li>
      </ul>
    </div>
  </section>
</template>
