<script lang="ts">
import { computed, defineComponent } from 'vue'

export default defineComponent({
  name: 'DeltaPill',
  props: {
    label: {
      type: String,
      required: true,
    },
    value: {
      type: Number,
      default: null,
    },
    digits: {
      type: Number,
      default: 2,
    },
  },
  setup(props) {
    const direction = computed(() => {
      if (props.value === null) {
        return 'flat'
      }

      if (props.value > 0) {
        return 'up'
      }

      if (props.value < 0) {
        return 'down'
      }

      return 'flat'
    })

    const iconName = computed(() => {
      if (direction.value === 'up') {
        return 'arrow-trend-up'
      }

      if (direction.value === 'down') {
        return 'arrow-trend-down'
      }

      return 'minus'
    })

    const toneClass = computed(() => {
      if (direction.value === 'up') {
        return 'border-[var(--accent-success)] bg-[color:color-mix(in_srgb,var(--accent-success),transparent_88%)] text-[var(--accent-success)]'
      }

      if (direction.value === 'down') {
        return 'border-[var(--accent-danger)] bg-[color:color-mix(in_srgb,var(--accent-danger),transparent_88%)] text-[var(--accent-danger)]'
      }

      return 'border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-secondary)]'
    })

    const formattedValue = computed(() => {
      if (props.value === null) {
        return 'N/A'
      }

      const sign = props.value > 0 ? '+' : ''
      return `${sign}${props.value.toFixed(props.digits)}%`
    })

    return {
      iconName,
      toneClass,
      formattedValue,
    }
  },
})
</script>

<template>
  <div class="inline-flex items-center gap-1 rounded border px-2 py-1 text-xs font-semibold" :class="toneClass">
    <FontAwesomeIcon :icon="['fas', iconName]" aria-hidden="true" />
    <span>{{ label }} {{ formattedValue }}</span>
  </div>
</template>
