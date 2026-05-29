<script setup lang="ts">
import { watch, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()
const savedMessage = ref('')
let clearTimer: ReturnType<typeof setTimeout> | null = null

watch(
  () => [ui.compactTables, ui.showHints, ui.notifications, ui.autoRefresh, ui.defaultTrainingMode],
  () => {
    ui.persistPreferences()
    savedMessage.value = 'Preferences saved.'

    if (clearTimer) {
      clearTimeout(clearTimer)
    }

    clearTimer = setTimeout(() => {
      savedMessage.value = ''
    }, 1_500)
  },
)
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="gear" title="Settings" subtitle="Theme, defaults, and operator preferences" />

    <p v-if="savedMessage" class="text-sm text-[var(--accent-success)]">{{ savedMessage }}</p>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Dashboard Preferences</h3>
      <div class="grid gap-3 text-sm md:grid-cols-2">
        <label class="check-row"><input v-model="ui.compactTables" type="checkbox" /><span class="check-label">Use compact table density</span></label>
        <label class="check-row"><input v-model="ui.showHints" type="checkbox" /><span class="check-label">Show inline training hints</span></label>
        <label class="check-row"><input v-model="ui.notifications" type="checkbox" /><span class="check-label">Enable browser notifications</span></label>
        <label class="check-row"><input v-model="ui.autoRefresh" type="checkbox" /><span class="check-label">Enable background auto-refresh</span></label>
      </div>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Training Defaults</h3>
      <label class="block max-w-xs space-y-1 text-sm">
        <span class="text-[var(--text-secondary)]">Default training mode</span>
        <select v-model="ui.defaultTrainingMode" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
          <option value="easy">Easy</option>
          <option value="advanced">Advanced</option>
        </select>
      </label>
    </section>
  </div>
</template>
