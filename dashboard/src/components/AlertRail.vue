<script lang="ts">
import { defineComponent } from 'vue'
import StatusBadge from './StatusBadge.vue'

type Severity = 'info' | 'warning' | 'critical' | 'success'

type AlertItem = {
  id: string
  severity: Severity
  title: string
  detail: string
  source: string
  timestamp: string
}

export default defineComponent({
  name: 'AlertRail',
  components: {
    StatusBadge,
  },
  props: {
    alerts: {
      type: Array as () => AlertItem[],
      required: true,
    },
  },
})
</script>

<template>
  <aside class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 shadow-sm" aria-label="Priority incidents and alerts">
    <div class="mb-2 flex items-center gap-2">
      <FontAwesomeIcon :icon="['fas', 'triangle-exclamation']" class="text-[var(--accent-warning)]" />
      <h2 class="text-sm font-semibold">Alert Rail</h2>
    </div>

    <ul class="space-y-2">
      <li v-for="alert in alerts" :key="alert.id" class="rounded border border-[var(--border-subtle)] p-2">
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p class="text-sm font-semibold">{{ alert.id }} | {{ alert.title }}</p>
            <p class="text-xs text-[var(--text-secondary)]">{{ alert.detail }}</p>
          </div>
          <StatusBadge
            :label="alert.severity.toUpperCase()"
            :severity="alert.severity"
            :source="alert.source"
            :timestamp="alert.timestamp"
          />
        </div>
      </li>
    </ul>
  </aside>
</template>
