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
      <p class="min-h-[1rem] min-w-[14rem] text-right text-xs text-[var(--text-secondary)]" :aria-hidden="!updatedAt">
        <span v-if="updatedAt">Updated {{ updatedAt }}</span>
        <span v-else class="invisible">Updated 0000-00-00T00:00:00.000Z</span>
      </p>
    </header>

    <div v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading...</div>
    <div v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</div>
    <div v-else>
      <slot />
    </div>
  </section>
</template>
