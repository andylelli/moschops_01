<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import PageHeader from '../components/PageHeader.vue'
import { apiGet } from '../api'

type ModelVersionResponse = {
  strategyId: string
  strategyVersion: string
  modelVersion: string
  lifecycleState: string
  createdAt: string
}

type PerformanceSnapshot = {
  id: string
  strategyId: string
  strategyVersion: string | null
  modelVersion: string | null
  expectancy: number | null
  profitFactor: number | null
  sharpe: number | null
  maxDrawdown: number | null
  tradeCount: number | null
  capturedAtUtc: string
}

type TrainingRun = {
  id: string
  trainingRunId: string
  strategyId: string
  modelVersion: string | null
  datasetVersion: string | null
  status: string
  metricsJson: Record<string, unknown> | null
  createdAt: string
}

type ScoreDistributionBin = {
  label: string
  lower: number
  upper: number
  count: number
}

const loading = ref(false)
const errorMessage = ref('')
const showNarrative = ref(false)
const activeModel = ref<ModelVersionResponse | null>(null)
const performance = ref<PerformanceSnapshot[]>([])
const trainingRuns = ref<TrainingRun[]>([])
const scoreBins = ref<ScoreDistributionBin[]>([])

const latestCompletedRun = computed(() => trainingRuns.value.find((run) => run.status === 'COMPLETED') ?? null)

const latestOutcome = computed(() => {
  const metricsJson = latestCompletedRun.value?.metricsJson
  if (!metricsJson || typeof metricsJson !== 'object') {
    return null
  }

  const outcome = (metricsJson as Record<string, unknown>).outcome
  if (!outcome || typeof outcome !== 'object') {
    return null
  }

  return outcome as Record<string, unknown>
})

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }

  return null
}

function getRunOutcomeMetric(run: TrainingRun, key: string): number | null {
  const metricsJson = run.metricsJson
  if (!metricsJson || typeof metricsJson !== 'object') {
    return null
  }

  const outcome = (metricsJson as Record<string, unknown>).outcome
  if (!outcome || typeof outcome !== 'object') {
    return null
  }

  return asNumber((outcome as Record<string, unknown>)[key])
}

const calibrationDrift = computed(() => {
  const drift = asNumber(latestOutcome.value?.calibrationDrift)
  return drift === null ? null : drift
})

const promotionCandidate = computed(() => {
  if (!latestCompletedRun.value?.modelVersion) {
    return 'N/A'
  }

  if (latestCompletedRun.value.modelVersion === activeModel.value?.modelVersion) {
    return `${latestCompletedRun.value.modelVersion} (already active)`
  }

  return latestCompletedRun.value.modelVersion
})

const latestPerformance = computed(() => performance.value[0] ?? null)

const scoreOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 26, right: 14, top: 18, bottom: 26 },
  xAxis: { type: 'category', data: scoreBins.value.map((item) => item.label) },
  yAxis: { type: 'value' },
  series: [
    {
      name: 'Predictions',
      type: 'bar',
      data: scoreBins.value.map((item) => item.count),
      barMaxWidth: 20,
    },
  ],
}))

async function loadAiModelsData() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [modelRes, performanceRes, trainingRes, scoreRes] = await Promise.all([
      apiGet<ModelVersionResponse>('/model-version'),
      apiGet<{ count: number; items: PerformanceSnapshot[] }>('/performance'),
      apiGet<{ count: number; items: TrainingRun[] }>('/training/runs?limit=20'),
      apiGet<{ count: number; bins: ScoreDistributionBin[] }>('/score-distribution?bins=10&lookback=1000'),
    ])

    activeModel.value = modelRes
    performance.value = performanceRes.items
    trainingRuns.value = trainingRes.items
    scoreBins.value = scoreRes.bins
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load AI metrics.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadAiModelsData()
})
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="microchip" title="AI and Models" subtitle="Model lifecycle, drift posture, and score distribution visibility" />

    <div class="flex flex-wrap justify-end gap-2">
      <button class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-sm" @click="showNarrative = true">
        How to read this page
      </button>
      <button
        class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-sm"
        :disabled="loading"
        @click="loadAiModelsData"
      >
        {{ loading ? 'Refreshing...' : 'Refresh AI Metrics' }}
      </button>
    </div>

    <p v-if="errorMessage" class="text-sm text-[var(--accent-danger)]">{{ errorMessage }}</p>

    <div class="grid gap-4 lg:grid-cols-3">
      <section
        class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm"
        title="Current model used by /signal for daily-breakout decision scoring."
      >
        <h2 class="mb-2 text-sm font-semibold">Active Model</h2>
        <p class="text-base font-semibold">{{ activeModel?.modelVersion ?? 'N/A' }}</p>
        <p class="text-sm text-[var(--text-secondary)]">Lifecycle: {{ activeModel?.lifecycleState ?? 'UNKNOWN' }}</p>
      </section>
      <section
        class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm"
        title="Calibration drift is |mean(predicted probability) - mean(observed outcome)| from latest completed training run."
      >
        <h2 class="mb-2 text-sm font-semibold">Calibration Drift</h2>
        <p class="text-base font-semibold">{{ calibrationDrift === null ? 'N/A' : calibrationDrift.toFixed(4) }}</p>
        <p class="text-sm text-[var(--text-secondary)]">
          {{ calibrationDrift === null ? 'No completed training metrics available' : calibrationDrift <= 0.05 ? 'Within warning threshold' : 'Review before promotion' }}
        </p>
      </section>
      <section
        class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm"
        title="Most recent trained model candidate available for promotion review."
      >
        <h2 class="mb-2 text-sm font-semibold">Promotion Candidate</h2>
        <p class="text-base font-semibold">{{ promotionCandidate }}</p>
        <p class="text-sm text-[var(--text-secondary)]">Pending risk gate review</p>
      </section>
    </div>

    <section class="grid gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm md:grid-cols-4">
      <article title="Latest out-of-sample AUC from completed training runs.">
        <p class="text-xs text-[var(--text-secondary)]">Latest AUC</p>
        <p class="text-lg font-semibold">{{ asNumber(latestOutcome?.aucMean) === null ? 'N/A' : asNumber(latestOutcome?.aucMean)?.toFixed(3) }}</p>
      </article>
      <article title="Latest Brier score from completed training runs.">
        <p class="text-xs text-[var(--text-secondary)]">Latest Brier</p>
        <p class="text-lg font-semibold">{{ asNumber(latestOutcome?.brierMean) === null ? 'N/A' : asNumber(latestOutcome?.brierMean)?.toFixed(4) }}</p>
      </article>
      <article title="Expectancy from latest performance snapshot.">
        <p class="text-xs text-[var(--text-secondary)]">Expectancy</p>
        <p class="text-lg font-semibold">{{ latestPerformance?.expectancy === null || latestPerformance?.expectancy === undefined ? 'N/A' : latestPerformance.expectancy.toFixed(3) }}</p>
      </article>
      <article title="Sharpe ratio from latest performance snapshot.">
        <p class="text-xs text-[var(--text-secondary)]">Sharpe</p>
        <p class="text-lg font-semibold">{{ latestPerformance?.sharpe === null || latestPerformance?.sharpe === undefined ? 'N/A' : latestPerformance.sharpe.toFixed(3) }}</p>
      </article>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h2 class="mb-2 text-sm font-semibold">Score Distribution</h2>
      <p v-if="scoreBins.length === 0" class="text-sm text-[var(--text-secondary)]">No prediction history available yet.</p>
      <div class="h-64 overflow-hidden">
        <VChart :option="scoreOption" autoresize class="h-full w-full" />
      </div>
    </section>

    <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h2 class="mb-2 text-sm font-semibold">Recent Training Sessions</h2>
      <div class="max-h-72 overflow-auto">
        <table class="min-w-full text-left text-xs">
          <thead class="text-[var(--text-secondary)]">
            <tr>
              <th class="py-2 pr-2">Run</th>
              <th class="py-2 pr-2">Status</th>
              <th class="py-2 pr-2">Dataset</th>
              <th class="py-2 pr-2">Model</th>
              <th class="py-2 pr-2">AUC</th>
              <th class="py-2 pr-2">Brier</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="trainingRuns.length === 0" class="border-t border-[var(--border-subtle)]">
              <td colspan="6" class="py-3 text-center text-[var(--text-secondary)]">No training sessions have been recorded yet.</td>
            </tr>
            <tr v-for="run in trainingRuns" :key="run.id" class="border-t border-[var(--border-subtle)]">
              <td class="py-2 pr-2">{{ run.trainingRunId }}</td>
              <td class="py-2 pr-2">{{ run.status }}</td>
              <td class="py-2 pr-2">{{ run.datasetVersion ?? 'N/A' }}</td>
              <td class="py-2 pr-2">{{ run.modelVersion ?? 'N/A' }}</td>
              <td class="py-2 pr-2">{{ getRunOutcomeMetric(run, 'aucMean') === null ? 'N/A' : getRunOutcomeMetric(run, 'aucMean')?.toFixed(3) }}</td>
              <td class="py-2 pr-2">{{ getRunOutcomeMetric(run, 'brierMean') === null ? 'N/A' : getRunOutcomeMetric(run, 'brierMean')?.toFixed(4) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div
      v-if="showNarrative"
      class="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
    >
      <article class="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-xl">
        <div class="mb-3 flex items-center justify-between gap-3">
          <h3 class="text-base font-semibold">AI and Models Guide</h3>
          <button class="rounded border border-[var(--border-subtle)] px-2 py-1 text-sm" @click="showNarrative = false">Close</button>
        </div>
        <div class="space-y-3 text-sm text-[var(--text-secondary)]">
          <p>
            Active Model shows the model currently used by the backend signal path. Promotion Candidate shows the latest trained model that can be reviewed for promotion.
          </p>
          <p>
            Calibration Drift is derived from the latest completed training run and indicates probability calibration quality. Lower values are better.
          </p>
          <p>
            Score Distribution shows prediction score concentration from persisted model predictions. Use it to monitor threshold sensitivity and class separation over time.
          </p>
          <p>
            Recent Training Sessions provides achieved metrics from each run so operators can compare model quality before promotion decisions.
          </p>
        </div>
      </article>
    </div>
  </div>
</template>
