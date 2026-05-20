<script setup lang="ts">
defineProps<{
  label: string
  value: string
  subtitle?: string
}>()
</script>

<template>
  <article class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
    <p class="text-xs text-[var(--text-secondary)]">{{ label }}</p>
    <p class="mt-1 text-2xl font-semibold">{{ value }}</p>
    <p v-if="subtitle" class="mt-1 text-xs text-[var(--text-secondary)]">{{ subtitle }}</p>
  </article>
</template>
