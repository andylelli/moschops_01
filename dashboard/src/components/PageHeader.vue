<script lang="ts">
import { defineComponent } from 'vue'

export default defineComponent({
  name: 'PageHeader',
  props: {
    icon: {
      type: String,
      required: true,
    },
    title: {
      type: String,
      required: true,
    },
    subtitle: {
      type: String,
      required: true,
    },
  },
})
</script>

<template>
  <header class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
    <h2 class="flex items-center gap-2 text-lg font-semibold">
      <FontAwesomeIcon :icon="['fas', icon]" class="text-sm text-[var(--accent-info)]" />
      {{ title }}
    </h2>
    <p class="mt-1 text-sm text-[var(--text-secondary)]">{{ subtitle }}</p>
  </header>
</template>
