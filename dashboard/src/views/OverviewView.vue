<script setup lang="ts">
import { onMounted, ref } from 'vue'
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
    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <h2 class="text-sm font-semibold">Temporarily Disabled</h2>
      <p class="mt-2 text-sm text-[var(--text-secondary)]">Account performance and AI drift widgets are disabled until their data feeds are live.</p>
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
