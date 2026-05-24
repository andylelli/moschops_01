<script lang="ts">
import { computed, defineComponent } from 'vue'
import StatusBadge from './StatusBadge.vue'

type KillSwitchState = 'normal' | 'armed' | 'tripped'

export default defineComponent({
  name: 'KillSwitchBanner',
  components: {
    StatusBadge,
  },
  props: {
    state: {
      type: String as () => KillSwitchState,
      required: true,
    },
    source: {
      type: String,
      default: 'risk-engine',
    },
    timestamp: {
      type: String,
      default: '',
    },
    reason: {
      type: String,
      default: 'No active override',
    },
  },
  setup(props) {
    const severity = computed(() => {
      if (props.state === 'tripped') return 'critical'
      if (props.state === 'armed') return 'warning'
      return 'success'
    })

    const label = computed(() => `Kill Switch ${props.state.toUpperCase()}`)

    return {
      severity,
      label,
    }
  },
})
</script>

<template>
  <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 shadow-sm">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <p class="text-xs text-[var(--text-secondary)]">Global Safety Posture</p>
        <p class="text-sm font-semibold">{{ reason }}</p>
      </div>
      <StatusBadge
        :label="label"
        :severity="severity"
        :source="source"
        :timestamp="timestamp"
      />
    </div>
  </section>
</template>
