<script setup lang="ts">
defineProps<{
  title: string
  loading?: boolean
  error?: string
  updatedAt?: string
}>()
</script>

<template>
  <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
    <header class="mb-3 flex items-center justify-between">
      <h2 class="text-sm font-semibold">{{ title }}</h2>
      <p v-if="updatedAt" class="text-xs text-[var(--text-secondary)]">Updated {{ updatedAt }}</p>
    </header>

    <div v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading...</div>
    <div v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</div>
    <div v-else>
      <slot />
    </div>
  </section>
</template>
