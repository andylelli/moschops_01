<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'IconLabel',
  props: {
    icon: {
      type: String,
      required: true,
    },
    label: {
      type: String,
      required: true,
    },
    subtitle: {
      type: String,
      default: '',
    },
    toneClass: {
      type: String,
      default: '',
    },
  },
})
</script>

<template>
  <div class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
    <p class="flex items-center gap-1 text-xs font-semibold" :class="toneClass">
      <FontAwesomeIcon :icon="['fas', icon]" aria-hidden="true" />
      <span>{{ label }}</span>
    </p>
    <p v-if="subtitle" class="mt-0.5 text-[11px] text-[var(--text-secondary)]">{{ subtitle }}</p>
  </div>
</template>
