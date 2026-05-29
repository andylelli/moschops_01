<script lang="ts">
import { defineComponent, type PropType } from 'vue'

export default defineComponent({
  name: 'EnvironmentSwitcher',
  props: {
    modelValue: {
      type: String,
      required: true,
    },
    options: {
      type: Array as PropType<string[]>,
      default: () => ['dev', 'demo', 'pilot', 'live'],
    },
  },
  emits: ['update:modelValue'],
  methods: {
    updateValue(event: Event) {
      const nextValue = (event.target as HTMLSelectElement).value
      this.$emit('update:modelValue', nextValue)
    },
  },
})
</script>

<template>
  <label class="space-y-0.5 text-xs">
    <span class="text-[var(--text-secondary)]">Environment</span>
    <select
      :value="modelValue"
      class="w-24 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm"
      aria-label="Environment selector"
      @change="updateValue"
    >
      <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
    </select>
  </label>
</template>
