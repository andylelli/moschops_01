<template>
  <div class="grid gap-4 lg:grid-cols-2">
    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <h2 class="mb-2 text-sm font-semibold">Kill-Switch Status</h2>
      <p class="text-sm">Status: Normal</p>
    </section>
    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <h2 class="mb-2 text-sm font-semibold">Recent Risk Events</h2>
      <p class="text-sm text-[var(--text-secondary)]">N/A: no risk events ingested yet.</p>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 lg:col-span-2">
      <h2 class="mb-2 text-sm font-semibold">Safety Checklist</h2>
      <div class="space-y-2 text-sm text-[var(--text-secondary)]">
        <label class="check-row">
          <input type="checkbox" disabled checked>
          <span class="check-label">Backend health probe reachable and returning healthy dependencies.</span>
        </label>
        <label class="check-row">
          <input type="checkbox" disabled>
          <span class="check-label">Model calibration report reviewed for current week before any pilot allocation changes.</span>
        </label>
        <label class="check-row">
          <input type="checkbox" disabled>
          <span class="check-label">Operator acknowledgement for kill-switch runbook.</span>
        </label>
      </div>
    </section>
  </div>
</template>
