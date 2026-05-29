<script lang="ts">
import { defineComponent, type PropType } from 'vue'

export default defineComponent({
  name: 'StrategyFilter',
  props: {
    modelValue: {
      type: String,
      required: true,
    },
    options: {
      type: Array as PropType<string[]>,
      required: true,
    },
  },
  emits: ['update:modelValue'],
  methods: {
    updateValue(event: Event) {
      this.$emit('update:modelValue', (event.target as HTMLSelectElement).value)
    },
  },
})
</script>

<template>
  <label class="space-y-0.5 text-xs">
    <span class="text-[var(--text-secondary)]">Strategy</span>
    <select
      :value="modelValue"
      class="w-44 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm"
      aria-label="Strategy selector"
      @change="updateValue"
    >
      <option v-for="item in options" :key="item" :value="item">{{ item }}</option>
    </select>
  </label>
</template>
