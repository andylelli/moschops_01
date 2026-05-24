<script setup lang="ts">
import PageHeader from '../components/PageHeader.vue'

const incidents = [
  {
    id: 'INC-2201',
    severity: 'WARNING',
    summary: 'Historical provider entitlement returned unsupported status',
    at: '2026-05-22T14:25:00Z',
    runbook: 'RB-NEWS-002',
  },
  {
    id: 'INC-2200',
    severity: 'INFO',
    summary: 'Model promotion candidate queued for approval',
    at: '2026-05-22T13:02:00Z',
    runbook: 'RB-ML-004',
  },
]

const runbookSteps = [
  'Confirm provider freshness and failure reason state from /health and /news/providers.',
  'Verify fail-closed posture still allows protective exits.',
  'Capture timeline evidence with UTC timestamps and request IDs.',
  'Escalate entitlement issue to provider contact and document ticket ID.',
]
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="triangle-exclamation" title="Incidents and Runbooks" subtitle="Operational timeline, response workflow, and acknowledgement context" />

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Incident Timeline</h3>
      <ul class="space-y-2 text-sm">
        <li v-for="incident in incidents" :key="incident.id" class="rounded border border-[var(--border-subtle)] p-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-semibold">{{ incident.id }}</span>
            <span class="rounded bg-[var(--bg-elevated)] px-2 py-0.5 text-xs">{{ incident.severity }}</span>
            <span class="text-xs text-[var(--text-secondary)]">{{ incident.at }}</span>
          </div>
          <p class="mt-1 text-[var(--text-secondary)]">{{ incident.summary }}</p>
          <p class="mt-1 text-xs">Runbook: <span class="font-semibold">{{ incident.runbook }}</span></p>
        </li>
      </ul>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Guided Runbook Steps</h3>
      <ol class="space-y-2 text-sm">
        <li v-for="(step, index) in runbookSteps" :key="step" class="rounded border border-[var(--border-subtle)] p-3">
          <span class="font-semibold">Step {{ index + 1 }}:</span> {{ step }}
        </li>
      </ol>
    </section>
  </div>
</template>
