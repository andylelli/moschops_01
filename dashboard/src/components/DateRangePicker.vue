<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'DateRangePicker',
  props: {
    startDate: {
      type: String,
      required: true,
    },
    endDate: {
      type: String,
      required: true,
    },
  },
  emits: ['update:startDate', 'update:endDate'],
  methods: {
    updateStartDate(event: Event) {
      this.$emit('update:startDate', (event.target as HTMLInputElement).value)
    },
    updateEndDate(event: Event) {
      this.$emit('update:endDate', (event.target as HTMLInputElement).value)
    },
  },
})
</script>

<template>
  <div class="grid grid-cols-2 gap-2 sm:flex sm:items-end">
    <label class="space-y-0.5 text-xs">
      <span class="text-[var(--text-secondary)]">Start date</span>
      <input
        :value="startDate"
        type="date"
        class="w-36 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm"
        aria-label="Start date"
        @input="updateStartDate"
      />
    </label>
    <label class="space-y-0.5 text-xs">
      <span class="text-[var(--text-secondary)]">End date</span>
      <input
        :value="endDate"
        type="date"
        class="w-36 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm"
        aria-label="End date"
        @input="updateEndDate"
      />
    </label>
  </div>
</template>
