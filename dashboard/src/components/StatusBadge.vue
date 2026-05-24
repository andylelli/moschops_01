<script lang="ts">
import { computed, defineComponent } from 'vue'

type Severity = 'info' | 'warning' | 'critical' | 'success'
type Freshness = 'fresh' | 'stale' | 'unavailable'

export default defineComponent({
  name: 'StatusBadge',
  props: {
    label: {
      type: String,
      required: true,
    },
    severity: {
      type: String as () => Severity,
      required: true,
    },
    source: {
      type: String,
      default: 'system',
    },
    timestamp: {
      type: String,
      default: '',
    },
    freshness: {
      type: String as () => Freshness,
      default: 'fresh',
    },
  },
  setup(props) {
    const iconName = computed(() => {
      if (props.severity === 'success') return 'circle-check'
      if (props.severity === 'warning') return 'triangle-exclamation'
      if (props.severity === 'critical') return 'circle-xmark'
      return 'circle-info'
    })

    const toneClass = computed(() => {
      if (props.severity === 'success') {
        return 'border-[var(--accent-success)] bg-[color:color-mix(in_srgb,var(--accent-success),transparent_88%)] text-[var(--accent-success)]'
      }

      if (props.severity === 'warning') {
        return 'border-[var(--accent-warning)] bg-[color:color-mix(in_srgb,var(--accent-warning),transparent_88%)] text-[var(--accent-warning)]'
      }

      if (props.severity === 'critical') {
        return 'border-[var(--accent-danger)] bg-[color:color-mix(in_srgb,var(--accent-danger),transparent_88%)] text-[var(--accent-danger)]'
      }

      return 'border-[var(--accent-info)] bg-[color:color-mix(in_srgb,var(--accent-info),transparent_88%)] text-[var(--accent-info)]'
    })

    const freshnessLabel = computed(() => {
      if (props.freshness === 'stale') return 'stale'
      if (props.freshness === 'unavailable') return 'unavailable'
      return 'fresh'
    })

    return {
      iconName,
      toneClass,
      freshnessLabel,
    }
  },
})
</script>

<template>
  <div class="rounded border px-2.5 py-1.5" :class="toneClass">
    <p class="flex items-center gap-1.5 text-xs font-semibold">
      <FontAwesomeIcon :icon="['fas', iconName]" aria-hidden="true" />
      <span>{{ label }}</span>
    </p>
    <p class="mt-0.5 text-[11px] text-[var(--text-secondary)]">
      Source {{ source }} | {{ freshnessLabel }}
      <span v-if="timestamp"> | {{ timestamp }}</span>
    </p>
  </div>
</template>
