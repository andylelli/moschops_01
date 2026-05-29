<script lang="ts">
import { defineComponent, type PropType } from 'vue'
import StatusBadge from './StatusBadge.vue'

type Severity = 'info' | 'warning' | 'critical' | 'success'

export default defineComponent({
  name: 'HealthTile',
  components: {
    StatusBadge,
  },
  props: {
    label: {
      type: String,
      required: true,
    },
    status: {
      type: String,
      required: true,
    },
    severity: {
      type: String as PropType<Severity>,
      required: true,
    },
    source: {
      type: String,
      required: true,
    },
    timestamp: {
      type: String,
      default: '',
    },
    details: {
      type: String,
      default: '',
    },
  },
})
</script>

<template>
  <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
    <div class="mb-2 flex items-start justify-between gap-2">
      <h3 class="text-sm font-semibold">{{ label }}</h3>
      <StatusBadge
        :label="status"
        :severity="severity"
        :source="source"
        :timestamp="timestamp"
      />
    </div>
    <p class="text-sm text-[var(--text-secondary)]">{{ details || 'No additional telemetry details.' }}</p>
  </section>
</template>
