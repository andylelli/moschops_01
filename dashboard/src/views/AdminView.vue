<script setup lang="ts">
import { ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import RoleGuard from '../components/RoleGuard.vue'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()

const approvals = [
  { id: 'APR-9001', action: 'Promote model xgb-2026-05-22', owner: 'ml-lead', scope: 'demo', state: 'Pending' },
  { id: 'APR-9002', action: 'Enable macro feature pack', owner: 'analyst-2', scope: 'pilot', state: 'Pending' },
]

const audits = [
  { id: 'AUD-8122', actor: 'admin-1', action: 'ROLLBACK_MODEL', reason: 'Drift spike > threshold', at: '2026-05-22T14:04:00Z' },
  { id: 'AUD-8117', actor: 'ml-lead', action: 'PROMOTE_MODEL', reason: 'All gates green', at: '2026-05-22T12:45:00Z' },
  { id: 'AUD-8102', actor: 'ops-lead', action: 'DISABLE_NEWS_SYNC', reason: 'Provider maintenance', at: '2026-05-22T09:10:00Z' },
]

const confirmationStep = ref<'closed' | 'confirm' | 'reason'>('closed')
const selectedApprovalId = ref('')
const reasonText = ref('')

function startApprovalFlow(approvalId: string) {
  selectedApprovalId.value = approvalId
  reasonText.value = ''
  confirmationStep.value = 'confirm'
}

function continueToReason() {
  confirmationStep.value = 'reason'
}

function cancelApprovalFlow() {
  confirmationStep.value = 'closed'
  selectedApprovalId.value = ''
  reasonText.value = ''
}

function finalizeApproval() {
  // This UI flow captures intent and reason before backend wiring is completed.
  cancelApprovalFlow()
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="user-shield" title="Admin" subtitle="Role-aware controls, approvals, and auditable operational changes" />

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Viewer accounts</p>
        <p class="mt-1 text-2xl font-semibold">14</p>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Analyst accounts</p>
        <p class="mt-1 text-2xl font-semibold">6</p>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Admin accounts</p>
        <p class="mt-1 text-2xl font-semibold">2</p>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Pending approvals</p>
        <p class="mt-1 text-2xl font-semibold">{{ approvals.length }}</p>
      </section>
    </div>

    <div class="grid gap-4 xl:grid-cols-3">
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm xl:col-span-2">
        <div class="mb-2 flex items-center justify-between">
          <h3 class="text-sm font-semibold">Approval Queue</h3>
          <p class="text-xs text-[var(--text-secondary)]">Role-gated with two-step confirmation and reason capture</p>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full text-left text-sm">
            <thead class="text-[var(--text-secondary)]">
              <tr>
                <th class="py-2 pr-4">ID</th>
                <th class="py-2 pr-4">Action</th>
                <th class="py-2 pr-4">Owner</th>
                <th class="py-2 pr-4">Scope</th>
                <th class="py-2 pr-4">State</th>
                <th class="py-2 pr-4">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in approvals" :key="row.id" class="border-t border-[var(--border-subtle)]">
                <td class="py-2 pr-4 font-semibold">{{ row.id }}</td>
                <td class="py-2 pr-4">{{ row.action }}</td>
                <td class="py-2 pr-4">{{ row.owner }}</td>
                <td class="py-2 pr-4">{{ row.scope }}</td>
                <td class="py-2 pr-4">{{ row.state }}</td>
                <td class="py-2 pr-4">
                  <RoleGuard :role="ui.operatorRole" :allowed-roles="['admin']" denied-message="Only admin can approve promotions, rollbacks, or disable actions.">
                    <button
                      class="rounded bg-[var(--accent-info)] px-2 py-1 text-xs font-semibold text-white"
                      @click="startApprovalFlow(row.id)"
                    >
                      Begin Approval
                    </button>
                  </RoleGuard>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h3 class="mb-2 text-sm font-semibold">Provider Entitlement Board</h3>
        <ul class="space-y-2 text-sm text-[var(--text-secondary)]">
          <li class="rounded border border-[var(--border-subtle)] p-2">
            <p class="font-semibold text-[var(--text-primary)]">FMP Tier</p>
            <p>FREE</p>
          </li>
          <li class="rounded border border-[var(--border-subtle)] p-2">
            <p class="font-semibold text-[var(--text-primary)]">Historical access</p>
            <p>Constrained (402/403 boundary)</p>
          </li>
          <li class="rounded border border-[var(--border-subtle)] p-2">
            <p class="font-semibold text-[var(--text-primary)]">Daily quota</p>
            <p>144/250 used</p>
          </li>
        </ul>
      </section>
    </div>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Audit Log Explorer</h3>
      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="text-[var(--text-secondary)]">
            <tr>
              <th class="py-2 pr-4">Event</th>
              <th class="py-2 pr-4">Actor</th>
              <th class="py-2 pr-4">Action</th>
              <th class="py-2 pr-4">Reason</th>
              <th class="py-2 pr-4">Timestamp (UTC)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in audits" :key="event.id" class="border-t border-[var(--border-subtle)]">
              <td class="py-2 pr-4 font-semibold">{{ event.id }}</td>
              <td class="py-2 pr-4">{{ event.actor }}</td>
              <td class="py-2 pr-4">{{ event.action }}</td>
              <td class="py-2 pr-4">{{ event.reason }}</td>
              <td class="py-2 pr-4">{{ event.at }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section
      v-if="confirmationStep !== 'closed'"
      class="rounded-lg border border-[var(--accent-warning)] bg-[color:color-mix(in_srgb,var(--accent-warning),transparent_92%)] p-4 shadow-sm"
    >
      <h3 class="mb-2 text-sm font-semibold">Privileged Action Confirmation</h3>
      <p class="text-sm text-[var(--text-secondary)]">Approval ID: {{ selectedApprovalId }}</p>

      <div v-if="confirmationStep === 'confirm'" class="mt-3 flex flex-wrap gap-2">
        <button class="rounded bg-[var(--accent-danger)] px-3 py-1 text-sm font-semibold text-white" @click="continueToReason">
          Confirm Step 1
        </button>
        <button class="rounded border border-[var(--border-subtle)] px-3 py-1 text-sm" @click="cancelApprovalFlow">
          Cancel
        </button>
      </div>

      <div v-else class="mt-3 space-y-2">
        <label class="block text-sm">
          <span class="text-[var(--text-secondary)]">Reason (required)</span>
          <textarea
            v-model="reasonText"
            class="mt-1 min-h-20 w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2"
            placeholder="Explain impact, rollback plan, and related incident or ticket IDs"
          />
        </label>

        <div class="flex flex-wrap gap-2">
          <button
            class="rounded bg-[var(--accent-success)] px-3 py-1 text-sm font-semibold text-white disabled:opacity-60"
            :disabled="reasonText.trim().length < 10"
            @click="finalizeApproval"
          >
            Confirm Step 2 and Submit
          </button>
          <button class="rounded border border-[var(--border-subtle)] px-3 py-1 text-sm" @click="cancelApprovalFlow">
            Cancel
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
