<script lang="ts">
import { defineComponent, type PropType } from 'vue'

export default defineComponent({
  name: 'IconActionButton',
  props: {
    icon: {
      type: String,
      required: true,
    },
    label: {
      type: String,
      required: true,
    },
    ariaLabel: {
      type: String,
      default: '',
    },
    variant: {
      type: String as PropType<'solid' | 'subtle'>,
      default: 'subtle',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['click'],
  methods: {
    onClick() {
      this.$emit('click')
    },
  },
})
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1 rounded border px-2 py-1 text-sm disabled:opacity-60"
    :class="
      variant === 'solid'
        ? 'border-transparent bg-[var(--accent-info)] text-white'
        : 'border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)]'
    "
    :aria-label="ariaLabel || label"
    :disabled="disabled"
    @click="onClick"
  >
    <FontAwesomeIcon :icon="['fas', icon]" aria-hidden="true" class="text-xs" />
    <span>{{ label }}</span>
  </button>
</template>
