<script setup lang="ts">
import { ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'

const preferences = ref({
  compactTables: true,
  showHints: true,
  notifications: false,
  autoRefresh: true,
  defaultMode: 'easy',
})
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="gear" title="Settings" subtitle="Theme, defaults, and operator preferences" />

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Dashboard Preferences</h3>
      <div class="grid gap-3 md:grid-cols-2 text-sm">
        <label class="check-row"><input v-model="preferences.compactTables" type="checkbox" /><span class="check-label">Use compact table density</span></label>
        <label class="check-row"><input v-model="preferences.showHints" type="checkbox" /><span class="check-label">Show inline training hints</span></label>
        <label class="check-row"><input v-model="preferences.notifications" type="checkbox" /><span class="check-label">Enable browser notifications</span></label>
        <label class="check-row"><input v-model="preferences.autoRefresh" type="checkbox" /><span class="check-label">Enable background auto-refresh</span></label>
      </div>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Training Defaults</h3>
      <label class="space-y-1 text-sm block max-w-xs">
        <span class="text-[var(--text-secondary)]">Default training mode</span>
        <select v-model="preferences.defaultMode" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
          <option value="easy">Easy</option>
          <option value="advanced">Advanced</option>
        </select>
      </label>
    </section>
  </div>
</template>
