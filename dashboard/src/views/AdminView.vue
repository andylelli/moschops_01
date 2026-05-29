<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiGet, apiPost } from '../api'
import PageHeader from '../components/PageHeader.vue'
import RoleGuard from '../components/RoleGuard.vue'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()

type ApprovalState = 'PENDING' | 'APPROVED' | 'REJECTED'

type ApprovalRow = {
  approvalId: string
  actionType: string
  actionLabel: string
  owner: string
  scope: string
  requestedBy: string
  requestedAtUtc: string
  state: ApprovalState
  decisionActor: string | null
  decisionReason: string | null
  decidedAtUtc: string | null
  strategyId: string | null
  strategyVersion: string | null
}

type ApprovalListResponse = {
  count: number
  items: ApprovalRow[]
}

type AuditRow = {
  eventId: string
  eventType: string
  reasonCode: string
  severity: string
  actor: string | null
  actionType: string | null
  reason: string | null
  createdAtUtc: string
}

type AuditListResponse = {
  count: number
  items: AuditRow[]
}

type ConfigSnapshot = {
  id: string
  strategyId: string
  strategyVersion: string
  riskProfile: string | null
  createdAtUtc: string
  config: unknown
}

type ConfigSnapshotResponse = {
  count: number
  items: ConfigSnapshot[]
}

type ProviderItem = {
  provider: string
  tier: string
  freshnessState: string
  failureReason: string | null
  budgetUsed: number | null
  budgetLimit: number | null
}

type ProviderResponse = {
  items: ProviderItem[]
}

type ApprovalSubmitResponse = {
  ok: boolean
  approval: ApprovalRow | null
}

type DecisionResponse = {
  ok: boolean
  approval: ApprovalRow | null
}

type RollbackResponse = {
  ok: boolean
  snapshot: ConfigSnapshot
}

const loading = ref(true)
const errorMessage = ref('')
const successMessage = ref('')

const approvals = ref<ApprovalRow[]>([])
const audits = ref<AuditRow[]>([])
const configSnapshots = ref<ConfigSnapshot[]>([])
const providerItems = ref<ProviderItem[]>([])

const submitRequest = ref({
  actionType: 'PROMOTE_MODEL',
  actionLabel: 'Promote latest validated model candidate',
  owner: 'ml-lead',
  scope: 'demo',
  reason: '',
})

const approvalDecisionType = ref<'approve' | 'reject'>('approve')
const confirmationStep = ref<'closed' | 'confirm' | 'reason'>('closed')
const selectedApprovalId = ref('')
const reasonText = ref('')

const rollbackStep = ref<'closed' | 'confirm' | 'reason'>('closed')
const rollbackConfigId = ref('')
const rollbackReason = ref('')

const pendingCount = computed(() => approvals.value.filter((item) => item.state === 'PENDING').length)
const latestProvider = computed(() => providerItems.value[0] ?? null)
const viewerAccounts = ref(14)
const analystAccounts = ref(6)
const adminAccounts = ref(2)

function toUiError(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected admin operation failure.'
}

async function loadAdminData() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [approvalRes, auditRes, snapshotRes, providerRes] = await Promise.all([
      apiGet<ApprovalListResponse>('/admin/approvals?state=ALL&limit=100'),
      apiGet<AuditListResponse>('/admin/audit-log?limit=100'),
      apiGet<ConfigSnapshotResponse>('/admin/config-snapshots?strategyId=daily-breakout-5-10&strategyVersion=1.0.0&limit=20'),
      apiGet<ProviderResponse>('/news/providers'),
    ])

    approvals.value = approvalRes.items
    audits.value = auditRes.items
    configSnapshots.value = snapshotRes.items
    providerItems.value = providerRes.items
  } catch (error) {
    errorMessage.value = toUiError(error)
  } finally {
    loading.value = false
  }
}

async function submitApprovalRequest() {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const response = await apiPost<
      {
        actionType: string
        actionLabel: string
        owner: string
        scope: string
        requestedBy: string
        reason: string
        strategyId: string
        strategyVersion: string
      },
      ApprovalSubmitResponse
    >('/admin/approvals/submit', {
      actionType: submitRequest.value.actionType,
      actionLabel: submitRequest.value.actionLabel,
      owner: submitRequest.value.owner,
      scope: submitRequest.value.scope,
      requestedBy: `${ui.operatorRole}-operator`,
      reason: submitRequest.value.reason,
      strategyId: 'daily-breakout-5-10',
      strategyVersion: '1.0.0',
    })

    if (!response.ok) {
      throw new Error('Approval request did not complete.')
    }

    successMessage.value = `Approval request ${response.approval?.approvalId ?? ''} submitted.`
    submitRequest.value.reason = ''
    await loadAdminData()
  } catch (error) {
    errorMessage.value = toUiError(error)
  }
}

function startApprovalFlow(approvalId: string, decisionType: 'approve' | 'reject') {
  approvalDecisionType.value = decisionType
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

async function finalizeApprovalDecision() {
  errorMessage.value = ''
  successMessage.value = ''

  const endpoint = approvalDecisionType.value === 'approve' ? 'approve' : 'reject'

  try {
    const response = await apiPost<{ actor: string; reason: string }, DecisionResponse>(
      `/admin/approvals/${selectedApprovalId.value}/${endpoint}`,
      {
        actor: ui.operatorRole,
        reason: reasonText.value,
      },
    )

    if (!response.ok) {
      throw new Error('Approval decision could not be persisted.')
    }

    successMessage.value = `Approval ${selectedApprovalId.value} ${approvalDecisionType.value === 'approve' ? 'approved' : 'rejected'}.`
    cancelApprovalFlow()
    await loadAdminData()
  } catch (error) {
    errorMessage.value = toUiError(error)
  }
}

function startRollbackFlow(configId: string) {
  rollbackConfigId.value = configId
  rollbackReason.value = ''
  rollbackStep.value = 'confirm'
}

function continueRollbackToReason() {
  rollbackStep.value = 'reason'
}

function cancelRollbackFlow() {
  rollbackStep.value = 'closed'
  rollbackConfigId.value = ''
  rollbackReason.value = ''
}

async function finalizeRollback() {
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const response = await apiPost<{ configId: string; actor: string; reason: string }, RollbackResponse>(
      '/admin/config-snapshots/rollback',
      {
        configId: rollbackConfigId.value,
        actor: ui.operatorRole,
        reason: rollbackReason.value,
      },
    )

    if (!response.ok) {
      throw new Error('Rollback operation failed.')
    }

    successMessage.value = `Rollback snapshot created: ${response.snapshot.id}`
    cancelRollbackFlow()
    await loadAdminData()
  } catch (error) {
    errorMessage.value = toUiError(error)
  }
}

onMounted(async () => {
  await loadAdminData()
})
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="user-shield" title="Admin" subtitle="Role-aware controls, approvals, and auditable operational changes" />

    <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading admin controls...</p>
    <p v-if="errorMessage" class="text-sm text-[var(--accent-danger)]">{{ errorMessage }}</p>
    <p v-if="successMessage" class="text-sm text-[var(--accent-success)]">{{ successMessage }}</p>

    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Viewer accounts</p>
        <p class="mt-1 text-2xl font-semibold">{{ viewerAccounts }}</p>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Analyst accounts</p>
        <p class="mt-1 text-2xl font-semibold">{{ analystAccounts }}</p>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Admin accounts</p>
        <p class="mt-1 text-2xl font-semibold">{{ adminAccounts }}</p>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <p class="text-xs text-[var(--text-secondary)]">Pending approvals</p>
        <p class="mt-1 text-2xl font-semibold">{{ pendingCount }}</p>
      </section>
    </div>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="mb-2 flex items-center justify-between gap-3">
        <h3 class="text-sm font-semibold">Submit Approval Request</h3>
        <RoleGuard :role="ui.operatorRole" :allowed-roles="['analyst', 'admin']" denied-message="Viewer role cannot submit approval requests.">
          <button
            class="rounded bg-[var(--accent-info)] px-3 py-1 text-sm font-semibold text-white disabled:opacity-60"
            :disabled="submitRequest.reason.trim().length < 10"
            @click="submitApprovalRequest"
          >
            Submit Request
          </button>
        </RoleGuard>
      </div>
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-5 text-sm">
        <label class="space-y-1">
          <span class="text-[var(--text-secondary)]">Action type</span>
          <select v-model="submitRequest.actionType" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
            <option value="PROMOTE_MODEL">PROMOTE_MODEL</option>
            <option value="ROLLBACK_MODEL">ROLLBACK_MODEL</option>
            <option value="DISABLE_FEATURE">DISABLE_FEATURE</option>
          </select>
        </label>
        <label class="space-y-1 xl:col-span-2">
          <span class="text-[var(--text-secondary)]">Action label</span>
          <input v-model="submitRequest.actionLabel" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
        </label>
        <label class="space-y-1">
          <span class="text-[var(--text-secondary)]">Owner</span>
          <input v-model="submitRequest.owner" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
        </label>
        <label class="space-y-1">
          <span class="text-[var(--text-secondary)]">Scope</span>
          <select v-model="submitRequest.scope" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
            <option value="demo">demo</option>
            <option value="pilot">pilot</option>
            <option value="live">live</option>
          </select>
        </label>
      </div>
      <label class="mt-3 block text-sm">
        <span class="text-[var(--text-secondary)]">Reason (required)</span>
        <textarea
          v-model="submitRequest.reason"
          class="mt-1 min-h-20 w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2"
          placeholder="Explain impact, rollback plan, and linked incident/ticket IDs"
        />
      </label>
    </section>

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
              <tr v-if="approvals.length === 0" class="border-t border-[var(--border-subtle)]">
                <td colspan="6" class="py-3 text-center text-[var(--text-secondary)]">No approval requests found.</td>
              </tr>
              <tr v-for="row in approvals" :key="row.approvalId" class="border-t border-[var(--border-subtle)]">
                <td class="py-2 pr-4 font-semibold">{{ row.approvalId }}</td>
                <td class="py-2 pr-4">{{ row.actionType }} - {{ row.actionLabel }}</td>
                <td class="py-2 pr-4">{{ row.owner }}</td>
                <td class="py-2 pr-4">{{ row.scope }}</td>
                <td class="py-2 pr-4">{{ row.state }}</td>
                <td class="py-2 pr-4">
                  <RoleGuard :role="ui.operatorRole" :allowed-roles="['admin']" denied-message="Only admin can approve promotions, rollbacks, or disable actions.">
                    <div class="flex flex-wrap gap-2">
                      <button
                        class="rounded bg-[var(--accent-success)] px-2 py-1 text-xs font-semibold text-white disabled:opacity-60"
                        :disabled="row.state !== 'PENDING'"
                        @click="startApprovalFlow(row.approvalId, 'approve')"
                      >
                        Approve
                      </button>
                      <button
                        class="rounded bg-[var(--accent-danger)] px-2 py-1 text-xs font-semibold text-white disabled:opacity-60"
                        :disabled="row.state !== 'PENDING'"
                        @click="startApprovalFlow(row.approvalId, 'reject')"
                      >
                        Reject
                      </button>
                    </div>
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
            <p>{{ latestProvider?.tier ?? 'N/A' }}</p>
          </li>
          <li class="rounded border border-[var(--border-subtle)] p-2">
            <p class="font-semibold text-[var(--text-primary)]">Historical access</p>
            <p>{{ latestProvider?.failureReason ?? 'Active' }}</p>
          </li>
          <li class="rounded border border-[var(--border-subtle)] p-2">
            <p class="font-semibold text-[var(--text-primary)]">Daily quota</p>
            <p>{{ latestProvider?.budgetUsed ?? 0 }}/{{ latestProvider?.budgetLimit ?? 'N/A' }} used</p>
          </li>
        </ul>
      </section>
    </div>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Configuration Snapshots and Rollback Controls</h3>
      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="text-[var(--text-secondary)]">
            <tr>
              <th class="py-2 pr-4">Snapshot ID</th>
              <th class="py-2 pr-4">Strategy</th>
              <th class="py-2 pr-4">Risk Profile</th>
              <th class="py-2 pr-4">Created (UTC)</th>
              <th class="py-2 pr-4">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="configSnapshots.length === 0" class="border-t border-[var(--border-subtle)]">
              <td colspan="5" class="py-3 text-center text-[var(--text-secondary)]">No config snapshots available.</td>
            </tr>
            <tr v-for="snapshot in configSnapshots" :key="snapshot.id" class="border-t border-[var(--border-subtle)]">
              <td class="py-2 pr-4 font-semibold">{{ snapshot.id }}</td>
              <td class="py-2 pr-4">{{ snapshot.strategyId }} v{{ snapshot.strategyVersion }}</td>
              <td class="py-2 pr-4">{{ snapshot.riskProfile ?? 'N/A' }}</td>
              <td class="py-2 pr-4">{{ snapshot.createdAtUtc }}</td>
              <td class="py-2 pr-4">
                <RoleGuard :role="ui.operatorRole" :allowed-roles="['admin']" denied-message="Only admin can execute rollback controls.">
                  <button class="rounded bg-[var(--accent-warning)] px-2 py-1 text-xs font-semibold text-white" @click="startRollbackFlow(snapshot.id)">
                    Begin Rollback
                  </button>
                </RoleGuard>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

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
            <tr v-if="audits.length === 0" class="border-t border-[var(--border-subtle)]">
              <td colspan="5" class="py-3 text-center text-[var(--text-secondary)]">No audit events captured.</td>
            </tr>
            <tr v-for="event in audits" :key="event.eventId" class="border-t border-[var(--border-subtle)]">
              <td class="py-2 pr-4 font-semibold">{{ event.eventId }}</td>
              <td class="py-2 pr-4">{{ event.actor ?? 'N/A' }}</td>
              <td class="py-2 pr-4">{{ event.actionType ?? event.eventType }}</td>
              <td class="py-2 pr-4">{{ event.reason ?? event.reasonCode }}</td>
              <td class="py-2 pr-4">{{ event.createdAtUtc }}</td>
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
            @click="finalizeApprovalDecision"
          >
            Confirm Step 2 and {{ approvalDecisionType === 'approve' ? 'Approve' : 'Reject' }}
          </button>
          <button class="rounded border border-[var(--border-subtle)] px-3 py-1 text-sm" @click="cancelApprovalFlow">
            Cancel
          </button>
        </div>
      </div>
    </section>

    <section
      v-if="rollbackStep !== 'closed'"
      class="rounded-lg border border-[var(--accent-warning)] bg-[color:color-mix(in_srgb,var(--accent-warning),transparent_92%)] p-4 shadow-sm"
    >
      <h3 class="mb-2 text-sm font-semibold">Rollback Confirmation</h3>
      <p class="text-sm text-[var(--text-secondary)]">Snapshot ID: {{ rollbackConfigId }}</p>

      <div v-if="rollbackStep === 'confirm'" class="mt-3 flex flex-wrap gap-2">
        <button class="rounded bg-[var(--accent-danger)] px-3 py-1 text-sm font-semibold text-white" @click="continueRollbackToReason">
          Confirm Step 1
        </button>
        <button class="rounded border border-[var(--border-subtle)] px-3 py-1 text-sm" @click="cancelRollbackFlow">
          Cancel
        </button>
      </div>

      <div v-else class="mt-3 space-y-2">
        <label class="block text-sm">
          <span class="text-[var(--text-secondary)]">Reason (required)</span>
          <textarea
            v-model="rollbackReason"
            class="mt-1 min-h-20 w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2"
            placeholder="Explain rollback impact and validation checks"
          />
        </label>

        <div class="flex flex-wrap gap-2">
          <button
            class="rounded bg-[var(--accent-success)] px-3 py-1 text-sm font-semibold text-white disabled:opacity-60"
            :disabled="rollbackReason.trim().length < 10"
            @click="finalizeRollback"
          >
            Confirm Step 2 and Rollback
          </button>
          <button class="rounded border border-[var(--border-subtle)] px-3 py-1 text-sm" @click="cancelRollbackFlow">
            Cancel
          </button>
        </div>
      </div>
    </section>
  </div>
</template>
