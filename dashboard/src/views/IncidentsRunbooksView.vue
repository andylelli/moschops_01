<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import DependencyGraph from '../components/DependencyGraph.vue'
import { apiGet, apiPost } from '../api'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()
const POLL_INTERVAL_MS = 20_000

type IncidentItem = {
  incidentId: string
  severity: string
  eventType: string
  reasonCode: string
  summary: string
  createdAtUtc: string
  runbookId: string
  acknowledged: boolean
  acknowledgedBy: string | null
  acknowledgedAtUtc: string | null
  latestNote: string | null
}

type IncidentResponse = {
  count: number
  items: IncidentItem[]
}

type GraphNode = {
  id: string
  label: string
  type: 'incident' | 'runbook'
  severity?: string
}

const loading = ref(true)
const error = ref('')
const successMessage = ref('')
const incidents = ref<IncidentItem[]>([])
const selectedIncidentId = ref<string | null>(null)
const acknowledgeNote = ref('')
const acknowledging = ref(false)
const updatedAt = ref('')

let pollTimer: ReturnType<typeof setInterval> | null = null

const runbookStepsMap: Record<string, string[]> = {
  'RB-NEWS-002': [
    'Confirm provider freshness and failure reason via /health and /news/providers.',
    'Verify fail-closed posture still permits protective exits for existing exposure.',
    'Capture UTC timeline evidence and provider ticket reference for audit trail.',
    'Escalate provider entitlement or feed failure using incident priority matrix.',
  ],
  'RB-RISK-001': [
    'Validate current kill-switch and portfolio guard status.',
    'Review veto reason concentration and open-risk consumption trend.',
    'Confirm no unsafe manual overrides are pending execution.',
    'Escalate to risk owner and document mitigation path with ETA.',
  ],
  'RB-ML-004': [
    'Check latest model diagnostics and calibration drift envelope.',
    'Verify promotion gates and fallback model availability.',
    'Review run artifacts and reproducibility metadata for anomalies.',
    'Log model governance decision with explicit rationale and owner.',
  ],
  'RB-ADMIN-003': [
    'Confirm actor, reason, and scoped blast radius are recorded.',
    'Validate rollback/promotion action status in approval timeline.',
    'Check post-action health and risk telemetry for regressions.',
    'Document closure with linked approval and configuration snapshot IDs.',
  ],
  'RB-GENERAL-001': [
    'Validate incident context and affected subsystem.',
    'Collect supporting UTC evidence and request traces.',
    'Assign owner and response deadline by severity.',
    'Record resolution details and verification checks.',
  ],
}

const selectedIncident = computed(() => {
  if (!selectedIncidentId.value) {
    return incidents.value[0] ?? null
  }

  return incidents.value.find((item) => item.incidentId === selectedIncidentId.value) ?? incidents.value[0] ?? null
})

const selectedRunbookSteps = computed(() => {
  const runbookId = selectedIncident.value?.runbookId ?? 'RB-GENERAL-001'
  return runbookStepsMap[runbookId] ?? runbookStepsMap['RB-GENERAL-001']
})

const graphNodes = computed(() => {
  const nodes: GraphNode[] = incidents.value.slice(0, 12).map((incident) => ({
    id: `incident-${incident.incidentId}`,
    label: `${incident.incidentId}\n${incident.severity.toUpperCase()}`,
    type: 'incident' as const,
    severity: incident.severity,
  }))

  const runbookIds = new Set(incidents.value.slice(0, 12).map((incident) => incident.runbookId))
  for (const runbookId of runbookIds) {
    nodes.push({
      id: `runbook-${runbookId}`,
      label: runbookId,
      type: 'runbook' as const,
    })
  }

  return nodes
})

const graphEdges = computed(() => {
  return incidents.value.slice(0, 12).map((incident) => ({
    id: `edge-${incident.incidentId}`,
    source: `incident-${incident.incidentId}`,
    target: `runbook-${incident.runbookId}`,
    label: incident.reasonCode,
  }))
})

async function loadIncidents() {
  loading.value = true
  error.value = ''

  try {
    const response = await apiGet<IncidentResponse>('/incidents?limit=80')
    incidents.value = response.items
    if (!selectedIncidentId.value && response.items.length > 0) {
      selectedIncidentId.value = response.items[0].incidentId
    }
    updatedAt.value = new Date().toISOString()
  } catch (e) {
    error.value = `N/A: ${(e as Error).message}`
  } finally {
    loading.value = false
  }
}

async function acknowledgeSelectedIncident() {
  if (!selectedIncident.value || acknowledgeNote.value.trim().length < 5) {
    return
  }

  acknowledging.value = true
  error.value = ''
  successMessage.value = ''

  try {
    await apiPost<{ actor: string; note: string }, { ok: boolean }>(
      `/incidents/${selectedIncident.value.incidentId}/acknowledge`,
      {
        actor: ui.operatorRole,
        note: acknowledgeNote.value.trim(),
      },
    )

    successMessage.value = `Incident ${selectedIncident.value.incidentId} acknowledged.`
    acknowledgeNote.value = ''
    await loadIncidents()
  } catch (e) {
    error.value = `Acknowledge failed: ${(e as Error).message}`
  } finally {
    acknowledging.value = false
  }
}

onMounted(() => {
  void loadIncidents()
  pollTimer = setInterval(() => {
    void loadIncidents()
  }, POLL_INTERVAL_MS)
})

onBeforeUnmount(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="triangle-exclamation" title="Incidents and Runbooks" subtitle="Live incident timeline, acknowledgements, and linked runbook execution" />

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
        <p class="text-[var(--text-secondary)]">Last updated (UTC): {{ updatedAt || 'N/A' }}</p>
        <button class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-1.5 text-sm" @click="loadIncidents">
          Refresh incidents
        </button>
      </div>
      <p v-if="error" class="mt-2 text-sm text-[var(--accent-danger)]">{{ error }}</p>
      <p v-if="successMessage" class="mt-2 text-sm text-[var(--accent-success)]">{{ successMessage }}</p>
    </section>

    <div class="grid gap-4 lg:grid-cols-2">
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h3 class="mb-2 text-sm font-semibold">Incident Timeline</h3>
        <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading incidents...</p>
        <ul v-else-if="incidents.length > 0" class="space-y-2 text-sm">
          <li
            v-for="incident in incidents"
            :key="incident.incidentId"
            class="cursor-pointer rounded border p-3"
            :class="selectedIncident?.incidentId === incident.incidentId ? 'border-[var(--accent-info)] bg-[var(--bg-elevated)]' : 'border-[var(--border-subtle)]'"
            tabindex="0"
            role="button"
            :aria-label="`Select incident ${incident.incidentId}`"
            @click="selectedIncidentId = incident.incidentId"
            @keydown.enter.prevent="selectedIncidentId = incident.incidentId"
            @keydown.space.prevent="selectedIncidentId = incident.incidentId"
          >
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-semibold">{{ incident.incidentId }}</span>
              <span class="rounded bg-[var(--bg-surface)] px-2 py-0.5 text-xs">{{ incident.severity.toUpperCase() }}</span>
              <span class="text-xs text-[var(--text-secondary)]">{{ incident.createdAtUtc }}</span>
              <span v-if="incident.acknowledged" class="rounded bg-[var(--bg-surface)] px-2 py-0.5 text-xs">
                Ack {{ incident.acknowledgedBy ?? 'unknown' }}
              </span>
            </div>
            <p class="mt-1 text-[var(--text-secondary)]">{{ incident.summary }}</p>
            <p class="mt-1 text-xs text-[var(--text-secondary)]">Runbook {{ incident.runbookId }} | {{ incident.reasonCode }}</p>
          </li>
        </ul>
        <p v-else class="text-sm text-[var(--text-secondary)]">No incident events available.</p>
      </section>

      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h3 class="mb-2 text-sm font-semibold">Runbook Guidance</h3>
        <p class="mb-2 text-xs text-[var(--text-secondary)]">
          Active runbook: <span class="font-semibold">{{ selectedIncident?.runbookId ?? 'RB-GENERAL-001' }}</span>
        </p>
        <ol class="space-y-2 text-sm">
          <li v-for="(step, index) in selectedRunbookSteps" :key="step" class="rounded border border-[var(--border-subtle)] p-3">
            <span class="font-semibold">Step {{ index + 1 }}:</span> {{ step }}
          </li>
        </ol>

        <div class="mt-4 rounded border border-[var(--border-subtle)] p-3">
          <h4 class="text-sm font-semibold">Operator Acknowledgement</h4>
          <p class="mt-1 text-xs text-[var(--text-secondary)]">Persist an auditable acknowledgement note for the selected incident.</p>
          <textarea
            v-model="acknowledgeNote"
            class="mt-2 w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-sm"
            rows="3"
            placeholder="Explain current status, owner, and next verification checkpoint"
          />
          <button
            class="mt-2 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="!selectedIncident || acknowledgeNote.trim().length < 5 || acknowledging"
            @click="acknowledgeSelectedIncident"
          >
            {{ acknowledging ? 'Acknowledging...' : 'Acknowledge Incident' }}
          </button>
        </div>
      </section>
    </div>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Incident Dependency Graph</h3>
      <p class="mb-2 text-xs text-[var(--text-secondary)]">Cytoscape lineage linking incident events to prescribed runbooks.</p>
      <DependencyGraph :nodes="graphNodes" :edges="graphEdges" :loading="loading" :error="error" />
    </section>
  </div>
</template>
