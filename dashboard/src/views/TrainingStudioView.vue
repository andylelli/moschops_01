<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import VChart from 'vue-echarts'
import PageHeader from '../components/PageHeader.vue'
import { apiGet, apiPost, apiPut } from '../api'

type Mode = 'easy' | 'advanced'

const mode = ref<Mode>('easy')
const selectedPreset = ref('Balanced Intraday')

const presets = [
  {
    name: 'Balanced Intraday',
    runtime: '12m',
    notes: 'Best default for first pass with stable precision/recall balance.',
  },
  {
    name: 'High Precision',
    runtime: '18m',
    notes: 'Fewer entries, stronger confirmation bias for risk-sensitive sessions.',
  },
  {
    name: 'High Recall',
    runtime: '16m',
    notes: 'Broader signal capture with downstream risk filters recommended.',
  },
]

const config = ref({
  datasetProfile: 'rolling-90d',
  horizonBars: 6,
  cvFolds: 5,
  calibration: 'isotonic',
  threshold: 0.62,
  includeMacro: true,
  includeNewsWindows: true,
  includeSessionFeatures: true,
  enableClassWeights: true,
})

const launchSummary = computed(() => {
  const base = mode.value === 'easy' ? 12 : 18
  const foldFactor = Math.max(0, config.value.cvFolds - 4)
  const runtime = base + foldFactor * 2
  const profile = mode.value === 'easy' ? 'Medium CPU / Low RAM' : 'High CPU / Medium RAM'
  return {
    runtime: `${runtime}m`,
    profile,
  }
})

type HistoricalJob = {
  id: string
  status: string
  source: string
  symbol: string
  timeframe: string
  fromDate: string
  toDate: string
  barsFetched: number
  barsInserted: number
  barsSkipped: number
  errorMessage: string | null
  requestedAtUtc: string
  completedAtUtc: string | null
}

type HistoricalBar = {
  id: string
  source: string
  symbol: string
  timeframe: string
  barCloseTimeUtc: string
  open: number
  high: number
  low: number
  close: number
  volume: number | null
}

type StrategyConfigResponse = {
  strategyId: string
  strategyVersion: string
  riskProfile: string
  source: 'default' | 'database'
  createdAt: string | null
  config: {
    aiThresholds: {
      full: number
      half: number
    }
    aiMandatory: boolean
    trainingDefaults: {
      datasetProfile: string
      horizonBars: number
      cvFolds: number
      calibration: 'isotonic' | 'platt' | 'none'
      threshold: number
      includeMacro: boolean
      includeNewsWindows: boolean
      includeSessionFeatures: boolean
      enableClassWeights: boolean
    }
  }
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

type TrainingDiagnostics = {
  confusionMatrix: {
    labels: [string, string]
    matrix: [[number, number], [number, number]]
    threshold: number
  }
  rocCurve: Array<{
    threshold: number
    fpr: number
    tpr: number
  }>
  prCurve: Array<{
    threshold: number
    recall: number
    precision: number
  }>
  calibrationBins: Array<{
    bucketStart: number
    bucketEnd: number
    predictedMean: number
    observedRate: number
    count: number
  }>
  featureImportance: Array<{
    feature: string
    importance: number
  }>
}

const historicalForm = ref({
  symbol: 'EURUSD',
  timeframe: 'D1',
  fromDate: '2024-01-01',
  toDate: new Date().toISOString().slice(0, 10),
  limit: '200',
  replaceExisting: false,
})

const historicalLoading = ref(false)
const historicalError = ref('')
const historicalSuccess = ref('')
const historicalJobs = ref<HistoricalJob[]>([])
const historicalBars = ref<HistoricalBar[]>([])
const showTrainingGuide = ref(false)
const showTrainingWizard = ref(false)
const wizardStep = ref(1)
const wizardError = ref('')
const wizardSavingAndLaunching = ref(false)
const wizardLaunchedRunId = ref('')

const wizardSteps = [
  { id: 1, title: 'Workflow' },
  { id: 2, title: 'Data and Validation' },
  { id: 3, title: 'Feature Toggles' },
  { id: 4, title: 'AI Runtime Policy' },
  { id: 5, title: 'Review and Launch' },
  { id: 6, title: 'Complete' },
]

const strategyRuntime = ref({
  strategyId: 'daily-breakout-5-10',
  strategyVersion: '1.0.0',
  riskProfile: 'balanced',
  aiThresholdFull: 0.65,
  aiThresholdHalf: 0.55,
  aiMandatory: false,
  source: 'default' as 'default' | 'database',
  updatedAtUtc: null as string | null,
})

const strategyConfigSaving = ref(false)
const strategyConfigStatus = ref('')
const strategyConfigError = ref('')

const trainingRuns = ref<TrainingRun[]>([])
const trainingLoading = ref(false)
const trainingError = ref('')
const trainingSuccess = ref('')

const wizardStepState = computed(() => {
  const current = wizardSteps.find((step) => step.id === wizardStep.value)
  return {
    currentTitle: current?.title ?? 'Workflow',
    isFirst: wizardStep.value === 1,
  }
})

const wizardProgressPercent = computed(() => Math.round((wizardStep.value / wizardSteps.length) * 100))

function toUiErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    if (error.message.includes('Failed to fetch')) {
      return 'Backend connection failed. Start backend at http://localhost:3000 and retry.'
    }

    return error.message
  }

  return 'Unexpected error while loading historical data.'
}

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

function getRunDiagnostics(run: TrainingRun): TrainingDiagnostics | null {
  const metricsJson = run.metricsJson
  if (!metricsJson || typeof metricsJson !== 'object') {
    return null
  }

  const diagnostics = (metricsJson as Record<string, unknown>).diagnostics
  if (!diagnostics || typeof diagnostics !== 'object') {
    return null
  }

  const source = diagnostics as Record<string, unknown>
  const confusion = source.confusionMatrix as Record<string, unknown> | undefined
  const matrix = confusion?.matrix as unknown
  const labels = confusion?.labels as unknown

  if (
    !Array.isArray(matrix) ||
    matrix.length !== 2 ||
    !Array.isArray(matrix[0]) ||
    !Array.isArray(matrix[1]) ||
    matrix[0].length !== 2 ||
    matrix[1].length !== 2 ||
    !Array.isArray(labels) ||
    labels.length !== 2
  ) {
    return null
  }

  const rocCurveRaw = Array.isArray(source.rocCurve) ? source.rocCurve : []
  const prCurveRaw = Array.isArray(source.prCurve) ? source.prCurve : []
  const calibrationRaw = Array.isArray(source.calibrationBins) ? source.calibrationBins : []
  const featureRaw = Array.isArray(source.featureImportance) ? source.featureImportance : []

  const rocCurve = rocCurveRaw
    .map((item) => {
      const point = item as Record<string, unknown>
      return {
        threshold: asNumber(point.threshold) ?? 0,
        fpr: asNumber(point.fpr) ?? 0,
        tpr: asNumber(point.tpr) ?? 0,
      }
    })
    .filter((point) => point.fpr >= 0 && point.tpr >= 0)

  const prCurve = prCurveRaw
    .map((item) => {
      const point = item as Record<string, unknown>
      return {
        threshold: asNumber(point.threshold) ?? 0,
        recall: asNumber(point.recall) ?? 0,
        precision: asNumber(point.precision) ?? 0,
      }
    })
    .filter((point) => point.recall >= 0 && point.precision >= 0)

  const calibrationBins = calibrationRaw
    .map((item) => {
      const bin = item as Record<string, unknown>
      return {
        bucketStart: asNumber(bin.bucketStart) ?? 0,
        bucketEnd: asNumber(bin.bucketEnd) ?? 0,
        predictedMean: asNumber(bin.predictedMean) ?? 0,
        observedRate: asNumber(bin.observedRate) ?? 0,
        count: Math.max(0, Math.round(asNumber(bin.count) ?? 0)),
      }
    })
    .filter((bin) => bin.bucketEnd > bin.bucketStart)

  const featureImportance = featureRaw
    .map((item) => {
      const feature = item as Record<string, unknown>
      return {
        feature: typeof feature.feature === 'string' ? feature.feature : 'unknown',
        importance: asNumber(feature.importance) ?? 0,
      }
    })
    .filter((item) => item.importance > 0)
    .sort((left, right) => right.importance - left.importance)

  return {
    confusionMatrix: {
      labels: [String(labels[0]), String(labels[1])],
      matrix: [
        [Math.max(0, Math.round(Number((matrix[0] as unknown[])[0]))), Math.max(0, Math.round(Number((matrix[0] as unknown[])[1])))],
        [Math.max(0, Math.round(Number((matrix[1] as unknown[])[0]))), Math.max(0, Math.round(Number((matrix[1] as unknown[])[1])))],
      ],
      threshold: asNumber(confusion?.threshold) ?? config.value.threshold,
    },
    rocCurve,
    prCurve,
    calibrationBins,
    featureImportance,
  }
}

const latestCompletedRun = computed(() => trainingRuns.value.find((run) => run.status === 'COMPLETED') ?? null)
const latestDiagnostics = computed(() => (latestCompletedRun.value ? getRunDiagnostics(latestCompletedRun.value) : null))

const rocCurveOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 24, bottom: 28 },
  xAxis: { type: 'value', min: 0, max: 1, name: 'FPR' },
  yAxis: { type: 'value', min: 0, max: 1, name: 'TPR' },
  series: [
    {
      name: 'ROC',
      type: 'line',
      smooth: false,
      symbol: 'none',
      data: (latestDiagnostics.value?.rocCurve ?? []).map((point) => [point.fpr, point.tpr]),
    },
    {
      name: 'Random Baseline',
      type: 'line',
      symbol: 'none',
      lineStyle: { type: 'dashed', opacity: 0.5 },
      data: [
        [0, 0],
        [1, 1],
      ],
    },
  ],
}))

const prCurveOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 24, bottom: 28 },
  xAxis: { type: 'value', min: 0, max: 1, name: 'Recall' },
  yAxis: { type: 'value', min: 0, max: 1, name: 'Precision' },
  series: [
    {
      name: 'PR',
      type: 'line',
      smooth: false,
      symbol: 'none',
      data: (latestDiagnostics.value?.prCurve ?? []).map((point) => [point.recall, point.precision]),
    },
  ],
}))

const calibrationOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 4 },
  grid: { left: 40, right: 20, top: 36, bottom: 24 },
  xAxis: {
    type: 'category',
    data: (latestDiagnostics.value?.calibrationBins ?? []).map(
      (bin) => `${bin.bucketStart.toFixed(1)}-${bin.bucketEnd.toFixed(1)}`,
    ),
  },
  yAxis: { type: 'value', min: 0, max: 1 },
  series: [
    {
      name: 'Predicted',
      type: 'bar',
      data: (latestDiagnostics.value?.calibrationBins ?? []).map((bin) => Number(bin.predictedMean.toFixed(4))),
      barMaxWidth: 18,
    },
    {
      name: 'Observed',
      type: 'line',
      data: (latestDiagnostics.value?.calibrationBins ?? []).map((bin) => Number(bin.observedRate.toFixed(4))),
      smooth: false,
      symbol: 'none',
    },
  ],
}))

const featureImportanceOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 120, right: 20, top: 16, bottom: 20 },
  xAxis: { type: 'value', min: 0, max: 1 },
  yAxis: {
    type: 'category',
    data: (latestDiagnostics.value?.featureImportance ?? []).map((item) => item.feature),
  },
  series: [
    {
      type: 'bar',
      data: (latestDiagnostics.value?.featureImportance ?? []).map((item) => Number(item.importance.toFixed(4))),
      barMaxWidth: 18,
    },
  ],
}))

const latestTrainingOutcome = computed(() => {
  if (!latestCompletedRun.value) {
    return {
      aucMean: null as number | null,
      brierMean: null as number | null,
      calibrationDrift: null as number | null,
      aucMin: null as number | null,
    }
  }

  return {
    aucMean: getRunOutcomeMetric(latestCompletedRun.value, 'aucMean'),
    brierMean: getRunOutcomeMetric(latestCompletedRun.value, 'brierMean'),
    calibrationDrift: getRunOutcomeMetric(latestCompletedRun.value, 'calibrationDrift'),
    aucMin: getRunOutcomeMetric(latestCompletedRun.value, 'aucMin'),
  }
})

const historicalBarsAscending = computed(() =>
  [...historicalBars.value].sort(
    (a, b) => Date.parse(a.barCloseTimeUtc) - Date.parse(b.barCloseTimeUtc),
  ),
)

const historicalSummary = computed(() => {
  if (historicalBars.value.length === 0) {
    return {
      barCount: 0,
      firstBarUtc: 'N/A',
      lastBarUtc: 'N/A',
      highestHigh: null as number | null,
      lowestLow: null as number | null,
    }
  }

  const highs = historicalBars.value.map((bar) => bar.high)
  const lows = historicalBars.value.map((bar) => bar.low)

  return {
    barCount: historicalBars.value.length,
    firstBarUtc: historicalBarsAscending.value[0]?.barCloseTimeUtc ?? 'N/A',
    lastBarUtc: historicalBarsAscending.value[historicalBarsAscending.value.length - 1]?.barCloseTimeUtc ?? 'N/A',
    highestHigh: Math.max(...highs),
    lowestLow: Math.min(...lows),
  }
})

const historicalPriceChartOption = computed(() => {
  const bars = historicalBarsAscending.value

  if (bars.length === 0) {
    return {
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: [{ type: 'line', data: [] }],
    }
  }

  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 36, right: 20, top: 18, bottom: 26 },
    xAxis: {
      type: 'category',
      data: bars.map((bar) => bar.barCloseTimeUtc.slice(0, 10)),
      axisLabel: { hideOverlap: true },
    },
    yAxis: { type: 'value', scale: true },
    series: [
      {
        name: 'Close',
        type: 'line',
        smooth: false,
        symbol: 'none',
        data: bars.map((bar) => Number(bar.close.toFixed(5))),
      },
      {
        name: 'High',
        type: 'line',
        smooth: false,
        symbol: 'none',
        lineStyle: { opacity: 0.45 },
        data: bars.map((bar) => Number(bar.high.toFixed(5))),
      },
      {
        name: 'Low',
        type: 'line',
        smooth: false,
        symbol: 'none',
        lineStyle: { opacity: 0.45 },
        data: bars.map((bar) => Number(bar.low.toFixed(5))),
      },
    ],
  }
})

async function loadHistoricalJobs() {
  const result = await apiGet<{ count: number; items: HistoricalJob[] }>('/historical-data/jobs?limit=20')
  historicalJobs.value = result.items
}

async function loadHistoricalBars() {
  const query = new URLSearchParams({
    source: 'FMP',
    symbol: historicalForm.value.symbol.toUpperCase(),
    timeframe: historicalForm.value.timeframe,
    fromDate: historicalForm.value.fromDate,
    toDate: historicalForm.value.toDate,
    limit: historicalForm.value.limit,
  })

  const result = await apiGet<{ count: number; items: HistoricalBar[] }>(`/historical-data/bars?${query.toString()}`)
  historicalBars.value = result.items
}

async function refreshHistoricalDataViews() {
  await Promise.all([loadHistoricalJobs(), loadHistoricalBars()])
}

async function refreshStoredBarsOnly() {
  historicalError.value = ''
  historicalSuccess.value = ''

  try {
    await loadHistoricalBars()
    historicalSuccess.value = 'Stored bars refreshed from database.'
  } catch (error) {
    historicalError.value = toUiErrorMessage(error)
  }
}

async function loadStrategyConfig() {
  const query = new URLSearchParams({
    strategyId: strategyRuntime.value.strategyId,
    strategyVersion: strategyRuntime.value.strategyVersion,
  })

  const profile = await apiGet<StrategyConfigResponse>(`/strategy-config/current?${query.toString()}`)
  strategyRuntime.value.riskProfile = profile.riskProfile
  strategyRuntime.value.aiThresholdFull = profile.config.aiThresholds.full
  strategyRuntime.value.aiThresholdHalf = profile.config.aiThresholds.half
  strategyRuntime.value.aiMandatory = profile.config.aiMandatory
  strategyRuntime.value.source = profile.source
  strategyRuntime.value.updatedAtUtc = profile.createdAt

  config.value.datasetProfile = profile.config.trainingDefaults.datasetProfile
  config.value.horizonBars = profile.config.trainingDefaults.horizonBars
  config.value.cvFolds = profile.config.trainingDefaults.cvFolds
  config.value.calibration = profile.config.trainingDefaults.calibration
  config.value.threshold = profile.config.trainingDefaults.threshold
  config.value.includeMacro = profile.config.trainingDefaults.includeMacro
  config.value.includeNewsWindows = profile.config.trainingDefaults.includeNewsWindows
  config.value.includeSessionFeatures = profile.config.trainingDefaults.includeSessionFeatures
  config.value.enableClassWeights = profile.config.trainingDefaults.enableClassWeights
}

async function saveStrategyConfig() {
  strategyConfigSaving.value = true
  strategyConfigStatus.value = ''
  strategyConfigError.value = ''

  if (strategyRuntime.value.aiThresholdHalf >= strategyRuntime.value.aiThresholdFull) {
    strategyConfigSaving.value = false
    strategyConfigError.value = 'Half threshold must be lower than full threshold.'
    return
  }

  try {
    const profile = await apiPut<
      {
        strategyId: string
        strategyVersion: string
        riskProfile: string
        config: StrategyConfigResponse['config']
      },
      StrategyConfigResponse
    >('/strategy-config/current', {
      strategyId: strategyRuntime.value.strategyId,
      strategyVersion: strategyRuntime.value.strategyVersion,
      riskProfile: strategyRuntime.value.riskProfile,
      config: {
        aiThresholds: {
          full: strategyRuntime.value.aiThresholdFull,
          half: strategyRuntime.value.aiThresholdHalf,
        },
        aiMandatory: strategyRuntime.value.aiMandatory,
        trainingDefaults: {
          datasetProfile: config.value.datasetProfile,
          horizonBars: config.value.horizonBars,
          cvFolds: config.value.cvFolds,
          calibration: config.value.calibration as 'isotonic' | 'platt' | 'none',
          threshold: config.value.threshold,
          includeMacro: config.value.includeMacro,
          includeNewsWindows: config.value.includeNewsWindows,
          includeSessionFeatures: config.value.includeSessionFeatures,
          enableClassWeights: config.value.enableClassWeights,
        },
      },
    })

    strategyRuntime.value.source = profile.source
    strategyRuntime.value.updatedAtUtc = profile.createdAt
    strategyConfigStatus.value = 'Strategy settings saved and persisted.'
  } catch (error) {
    strategyConfigError.value = toUiErrorMessage(error)
  } finally {
    strategyConfigSaving.value = false
  }
}

async function loadTrainingRuns() {
  const result = await apiGet<{ count: number; items: TrainingRun[] }>('/training/runs?limit=20')
  trainingRuns.value = result.items
}

async function launchTrainingRun(): Promise<TrainingRun | null> {
  trainingLoading.value = true
  trainingError.value = ''
  trainingSuccess.value = ''

  try {
    const result = await apiPost<
      {
        strategyId: string
        strategyVersion: string
        mode: Mode
        presetName: string
        datasetProfile: string
        horizonBars: number
        cvFolds: number
        calibration: 'isotonic' | 'platt' | 'none'
        threshold: number
        includeMacro: boolean
        includeNewsWindows: boolean
        includeSessionFeatures: boolean
        enableClassWeights: boolean
      },
      { run: TrainingRun }
    >('/training/runs', {
      strategyId: strategyRuntime.value.strategyId,
      strategyVersion: strategyRuntime.value.strategyVersion,
      mode: mode.value,
      presetName: selectedPreset.value,
      datasetProfile: config.value.datasetProfile,
      horizonBars: config.value.horizonBars,
      cvFolds: config.value.cvFolds,
      calibration: config.value.calibration as 'isotonic' | 'platt' | 'none',
      threshold: config.value.threshold,
      includeMacro: config.value.includeMacro,
      includeNewsWindows: config.value.includeNewsWindows,
      includeSessionFeatures: config.value.includeSessionFeatures,
      enableClassWeights: config.value.enableClassWeights,
    })

    trainingSuccess.value = `Training session ${result.run.trainingRunId} completed and metrics were recorded.`
    await loadTrainingRuns()
    return result.run
  } catch (error) {
    trainingError.value = toUiErrorMessage(error)
    return null
  } finally {
    trainingLoading.value = false
  }
}

function openTrainingWizard() {
  wizardStep.value = 1
  wizardError.value = ''
  wizardLaunchedRunId.value = ''
  showTrainingWizard.value = true
}

function closeTrainingWizard() {
  showTrainingWizard.value = false
  wizardStep.value = 1
  wizardError.value = ''
  wizardSavingAndLaunching.value = false
  wizardLaunchedRunId.value = ''
}

function validateWizardStep(step: number): string | null {
  if (step === 2) {
    if (config.value.horizonBars < 1 || config.value.horizonBars > 64) {
      return 'Horizon bars must be between 1 and 64.'
    }

    if (config.value.cvFolds < 2 || config.value.cvFolds > 20) {
      return 'CV folds must be between 2 and 20.'
    }

    if (config.value.threshold <= 0 || config.value.threshold > 1) {
      return 'Decision threshold must be in range (0, 1].'
    }
  }

  if (step === 4) {
    if (strategyRuntime.value.aiThresholdHalf <= 0 || strategyRuntime.value.aiThresholdHalf > 1) {
      return 'AI half threshold must be in range (0, 1].'
    }

    if (strategyRuntime.value.aiThresholdFull <= 0 || strategyRuntime.value.aiThresholdFull > 1) {
      return 'AI full threshold must be in range (0, 1].'
    }

    if (strategyRuntime.value.aiThresholdHalf >= strategyRuntime.value.aiThresholdFull) {
      return 'AI half threshold must be lower than AI full threshold.'
    }
  }

  return null
}

function wizardNextStep() {
  if (wizardStep.value >= 5) {
    return
  }

  const validationError = validateWizardStep(wizardStep.value)
  if (validationError) {
    wizardError.value = validationError
    return
  }

  wizardError.value = ''
  wizardStep.value = Math.min(wizardStep.value + 1, wizardSteps.length)
}

function wizardPreviousStep() {
  wizardError.value = ''
  wizardStep.value = Math.max(1, wizardStep.value - 1)
}

async function wizardSaveAndLaunch() {
  wizardError.value = ''

  for (const step of wizardSteps) {
    if (step.id === wizardSteps.length) {
      continue
    }

    const validationError = validateWizardStep(step.id)
    if (validationError) {
      wizardStep.value = step.id
      wizardError.value = validationError
      return
    }
  }

  wizardSavingAndLaunching.value = true

  await saveStrategyConfig()
  if (strategyConfigError.value) {
    wizardError.value = strategyConfigError.value
    wizardSavingAndLaunching.value = false
    return
  }

  const run = await launchTrainingRun()
  if (!run || trainingError.value) {
    wizardError.value = trainingError.value || 'Training launch failed.'
    wizardSavingAndLaunching.value = false
    return
  }

  wizardLaunchedRunId.value = run.trainingRunId
  wizardSavingAndLaunching.value = false
  wizardStep.value = 6
}

function closeTrainingGuide() {
  showTrainingGuide.value = false
}

function jumpToStudioSection(sectionId: string) {
  closeTrainingWizard()
  requestAnimationFrame(() => {
    const element = document.getElementById(sectionId)
    element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') {
    return
  }

  if (showTrainingWizard.value) {
    closeTrainingWizard()
    event.preventDefault()
    return
  }

  if (showTrainingGuide.value) {
    closeTrainingGuide()
    event.preventDefault()
  }
}

async function startHistoricalDownload() {
  historicalLoading.value = true
  historicalError.value = ''
  historicalSuccess.value = ''

  try {
    const result = await apiPost<
      {
        source: string
        symbol: string
        timeframe: string
        fromDate: string
        toDate: string
        replaceExisting: boolean
        requestedBy: string
      },
      { job: HistoricalJob }
    >('/historical-data/download', {
      source: 'FMP',
      symbol: historicalForm.value.symbol.toUpperCase(),
      timeframe: historicalForm.value.timeframe,
      fromDate: historicalForm.value.fromDate,
      toDate: historicalForm.value.toDate,
      replaceExisting: historicalForm.value.replaceExisting,
      requestedBy: 'dashboard-operator',
    })

    historicalSuccess.value = `Download completed. Inserted ${result.job.barsInserted} bars (${result.job.barsSkipped} duplicates skipped).`
    await refreshHistoricalDataViews()
  } catch (error) {
    historicalError.value = toUiErrorMessage(error)
    try {
      await loadHistoricalJobs()
    } catch {
      // Keep primary error visible if jobs refresh also fails.
    }
  } finally {
    historicalLoading.value = false
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleGlobalKeydown)

  try {
    await refreshHistoricalDataViews()
  } catch (error) {
    historicalError.value = toUiErrorMessage(error)
  }

  try {
    await loadStrategyConfig()
  } catch (error) {
    strategyConfigError.value = toUiErrorMessage(error)
  }

  try {
    await loadTrainingRuns()
  } catch (error) {
    trainingError.value = toUiErrorMessage(error)
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="flask" title="Training Studio" subtitle="Easy presets, advanced controls, and rich diagnostics for fast model iteration" />

    <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex items-center gap-2">
            <button
              class="rounded px-3 py-1 text-sm"
              :class="mode === 'easy' ? 'bg-[var(--accent-info)] text-white' : 'bg-[var(--bg-elevated)]'"
              @click="mode = 'easy'"
            >
              Easy Mode
            </button>
            <button
              class="rounded px-3 py-1 text-sm"
              :class="mode === 'advanced' ? 'bg-[var(--accent-info)] text-white' : 'bg-[var(--bg-elevated)]'"
              @click="mode = 'advanced'"
            >
              Advanced Mode
            </button>
          </div>
          <button class="rounded border border-[var(--border-subtle)] px-3 py-1 text-sm" @click="openTrainingWizard">
            Open Training Wizard
          </button>
          <button class="rounded border border-[var(--border-subtle)] px-3 py-1 text-sm" @click="showTrainingGuide = true">
            Training Guide
          </button>
        </div>
        <div class="text-sm text-[var(--text-secondary)]">
          Estimated runtime: <span class="font-semibold text-[var(--text-primary)]">{{ launchSummary.runtime }}</span>
          | Resource: <span class="font-semibold text-[var(--text-primary)]">{{ launchSummary.profile }}</span>
        </div>
      </div>
      <p class="mt-2 text-xs text-[var(--text-secondary)]">
        Strategy {{ strategyRuntime.strategyId }} v{{ strategyRuntime.strategyVersion }} | Config source: {{ strategyRuntime.source }}
      </p>
    </section>

    <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="text-sm font-semibold">Historical Data Download</h3>
          <p class="text-xs text-[var(--text-secondary)]">Download bars from provider and persist to PostgreSQL by symbol, timeframe, and date range.</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-sm font-semibold"
            :disabled="historicalLoading"
            @click="refreshStoredBarsOnly"
          >
            Refresh Stored Bars
          </button>
          <button
            class="rounded bg-[var(--accent-info)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
            :disabled="historicalLoading"
            @click="startHistoricalDownload"
          >
            {{ historicalLoading ? 'Downloading...' : 'Download Historical Data' }}
          </button>
        </div>
      </div>

      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <label class="space-y-1 text-sm">
          <span class="text-[var(--text-secondary)]">Symbol</span>
          <input
            v-model="historicalForm.symbol"
            class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1"
            placeholder="EURUSD"
          />
        </label>

        <label class="space-y-1 text-sm">
          <span class="text-[var(--text-secondary)]">Timeframe</span>
          <select v-model="historicalForm.timeframe" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
            <option value="M15">M15</option>
            <option value="H1">H1</option>
            <option value="H4">H4</option>
            <option value="D1">D1</option>
          </select>
        </label>

        <label class="space-y-1 text-sm">
          <span class="text-[var(--text-secondary)]">From date</span>
          <input v-model="historicalForm.fromDate" type="date" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
        </label>

        <label class="space-y-1 text-sm">
          <span class="text-[var(--text-secondary)]">To date</span>
          <input v-model="historicalForm.toDate" type="date" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
        </label>

        <label class="space-y-1 text-sm">
          <span class="text-[var(--text-secondary)]">Bars to display</span>
          <select v-model="historicalForm.limit" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
            <option value="50">50</option>
            <option value="200">200</option>
            <option value="500">500</option>
            <option value="1000">1000</option>
          </select>
        </label>

        <label class="check-row mt-6">
          <input v-model="historicalForm.replaceExisting" type="checkbox" />
          <span class="check-label text-sm">Replace existing bars in selected range</span>
        </label>
      </div>

      <p v-if="historicalError" class="mt-3 text-sm text-[var(--accent-danger)]">{{ historicalError }}</p>
      <p v-if="historicalSuccess" class="mt-3 text-sm text-[var(--accent-success)]">{{ historicalSuccess }}</p>

      <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4 text-sm">
        <section class="rounded border border-[var(--border-subtle)] p-2">
          <p class="text-[var(--text-secondary)]">Bars loaded</p>
          <p class="font-semibold">{{ historicalSummary.barCount }}</p>
        </section>
        <section class="rounded border border-[var(--border-subtle)] p-2">
          <p class="text-[var(--text-secondary)]">First bar UTC</p>
          <p class="font-semibold">{{ historicalSummary.firstBarUtc }}</p>
        </section>
        <section class="rounded border border-[var(--border-subtle)] p-2">
          <p class="text-[var(--text-secondary)]">Last bar UTC</p>
          <p class="font-semibold">{{ historicalSummary.lastBarUtc }}</p>
        </section>
        <section class="rounded border border-[var(--border-subtle)] p-2">
          <p class="text-[var(--text-secondary)]">Range (low/high)</p>
          <p class="font-semibold">
            {{ historicalSummary.lowestLow === null ? 'N/A' : historicalSummary.lowestLow.toFixed(5) }} /
            {{ historicalSummary.highestHigh === null ? 'N/A' : historicalSummary.highestHigh.toFixed(5) }}
          </p>
        </section>
      </div>

      <section class="mt-4 rounded border border-[var(--border-subtle)] p-3">
        <h4 class="mb-2 text-sm font-semibold">Historical Price Preview</h4>
        <p v-if="historicalBars.length === 0" class="text-xs text-[var(--text-secondary)]">
          No bars currently loaded for the selected filter set.
        </p>
        <div v-else class="h-64 overflow-hidden">
          <VChart :option="historicalPriceChartOption" autoresize class="h-full w-full" />
        </div>
      </section>

      <div class="mt-4 grid gap-4 xl:grid-cols-2">
        <section class="rounded border border-[var(--border-subtle)] p-3">
          <h4 class="mb-2 text-sm font-semibold">Recent Download Jobs</h4>
          <div class="max-h-72 overflow-auto">
            <table class="min-w-full text-left text-xs">
              <thead class="text-[var(--text-secondary)]">
                <tr>
                  <th class="py-2 pr-2">Status</th>
                  <th class="py-2 pr-2">Symbol</th>
                  <th class="py-2 pr-2">TF</th>
                  <th class="py-2 pr-2">Inserted</th>
                  <th class="py-2 pr-2">Skipped</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="job in historicalJobs" :key="job.id" class="border-t border-[var(--border-subtle)]">
                  <td class="py-2 pr-2 font-semibold">{{ job.status }}</td>
                  <td class="py-2 pr-2">{{ job.symbol }}</td>
                  <td class="py-2 pr-2">{{ job.timeframe }}</td>
                  <td class="py-2 pr-2">{{ job.barsInserted }}</td>
                  <td class="py-2 pr-2">{{ job.barsSkipped }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="rounded border border-[var(--border-subtle)] p-3">
          <h4 class="mb-2 text-sm font-semibold">Stored Bars (Current Selection)</h4>
          <div class="max-h-72 overflow-auto">
            <table class="min-w-full text-left text-xs">
              <thead class="text-[var(--text-secondary)]">
                <tr>
                  <th class="py-2 pr-2">Bar close UTC</th>
                  <th class="py-2 pr-2">Open</th>
                  <th class="py-2 pr-2">High</th>
                  <th class="py-2 pr-2">Low</th>
                  <th class="py-2 pr-2">Close</th>
                  <th class="py-2 pr-2">Volume</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="historicalBars.length === 0" class="border-t border-[var(--border-subtle)]">
                  <td colspan="6" class="py-3 text-center text-[var(--text-secondary)]">No stored bars for current filter.</td>
                </tr>
                <tr v-for="bar in historicalBars" :key="bar.id" class="border-t border-[var(--border-subtle)]">
                  <td class="py-2 pr-2">{{ bar.barCloseTimeUtc }}</td>
                  <td class="py-2 pr-2">{{ bar.open.toFixed(5) }}</td>
                  <td class="py-2 pr-2">{{ bar.high.toFixed(5) }}</td>
                  <td class="py-2 pr-2">{{ bar.low.toFixed(5) }}</td>
                  <td class="py-2 pr-2">{{ bar.close.toFixed(5) }}</td>
                  <td class="py-2 pr-2">{{ bar.volume === null ? 'N/A' : bar.volume }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </section>

    <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 class="text-sm font-semibold">Strategy Runtime Settings</h3>
          <p class="text-xs text-[var(--text-secondary)]">Persisted settings used by signal thresholding and training defaults.</p>
        </div>
        <button
          class="rounded bg-[var(--accent-info)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          :disabled="strategyConfigSaving"
          @click="saveStrategyConfig"
        >
          {{ strategyConfigSaving ? 'Saving...' : 'Save Strategy Settings' }}
        </button>
      </div>

      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label class="space-y-1 text-sm" title="Score at or above this value uses full position sizing.">
          <span class="text-[var(--text-secondary)]">AI full threshold</span>
          <input v-model.number="strategyRuntime.aiThresholdFull" type="number" min="0.01" max="1" step="0.01" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
        </label>

        <label class="space-y-1 text-sm" title="Score between half and full thresholds uses half sizing; below half is skipped.">
          <span class="text-[var(--text-secondary)]">AI half threshold</span>
          <input v-model.number="strategyRuntime.aiThresholdHalf" type="number" min="0.01" max="1" step="0.01" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
        </label>

        <label class="space-y-1 text-sm" title="Risk profile tag used for operator context and future profile-based policy wiring.">
          <span class="text-[var(--text-secondary)]">Risk profile</span>
          <select v-model="strategyRuntime.riskProfile" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
            <option value="conservative">conservative</option>
            <option value="balanced">balanced</option>
            <option value="active">active</option>
          </select>
        </label>

        <label class="check-row mt-6" title="When enabled, no new entries are allowed if AI scoring is unavailable.">
          <input v-model="strategyRuntime.aiMandatory" type="checkbox" />
          <span class="check-label text-sm">AI mandatory mode</span>
        </label>
      </div>

      <p class="mt-2 text-xs text-[var(--text-secondary)]">
        Last persisted: {{ strategyRuntime.updatedAtUtc ?? 'Not yet persisted in DB' }}
      </p>
      <p v-if="strategyConfigStatus" class="mt-2 text-sm text-[var(--accent-success)]">{{ strategyConfigStatus }}</p>
      <p v-if="strategyConfigError" class="mt-2 text-sm text-[var(--accent-danger)]">{{ strategyConfigError }}</p>
    </section>

    <div class="grid gap-4 xl:grid-cols-3">
      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm xl:col-span-2">
        <h3 class="mb-3 text-sm font-semibold">Preset Launcher</h3>
        <div class="grid gap-3 md:grid-cols-3">
          <button
            v-for="preset in presets"
            :key="preset.name"
            class="rounded-lg border border-[var(--border-subtle)] p-3 text-left"
            :class="selectedPreset === preset.name ? 'bg-[color:color-mix(in_srgb,var(--accent-info),transparent_88%)]' : 'bg-[var(--bg-surface)]'"
            @click="selectedPreset = preset.name"
          >
            <p class="font-semibold">{{ preset.name }}</p>
            <p class="text-xs text-[var(--text-secondary)]">Run time {{ preset.runtime }}</p>
            <p class="mt-2 text-xs text-[var(--text-secondary)]">{{ preset.notes }}</p>
          </button>
        </div>
      </section>

      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h3 class="mb-3 text-sm font-semibold">Launch Summary</h3>
        <ul class="space-y-2 text-sm">
          <li>Preset: <span class="font-semibold">{{ selectedPreset }}</span></li>
          <li>Data profile: <span class="font-semibold">{{ config.datasetProfile }}</span></li>
          <li>CV folds: <span class="font-semibold">{{ config.cvFolds }}</span></li>
          <li>Threshold: <span class="font-semibold">{{ config.threshold.toFixed(2) }}</span></li>
        </ul>
        <button
          class="mt-4 w-full rounded bg-[var(--accent-success)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          :disabled="trainingLoading"
          @click="launchTrainingRun"
        >
          {{ trainingLoading ? 'Launching...' : 'Launch Training Run' }}
        </button>
        <p v-if="trainingSuccess" class="mt-2 text-sm text-[var(--accent-success)]">{{ trainingSuccess }}</p>
        <p v-if="trainingError" class="mt-2 text-sm text-[var(--accent-danger)]">{{ trainingError }}</p>
      </section>
    </div>

    <section class="grid gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 text-sm shadow-sm md:grid-cols-4">
      <article title="Latest out-of-sample AUC from completed training sessions.">
        <p class="text-[var(--text-secondary)]">Latest AUC</p>
        <p class="font-semibold">{{ latestTrainingOutcome.aucMean === null ? 'N/A' : latestTrainingOutcome.aucMean.toFixed(3) }}</p>
      </article>
      <article title="Latest out-of-sample Brier score from completed training sessions.">
        <p class="text-[var(--text-secondary)]">Latest Brier</p>
        <p class="font-semibold">{{ latestTrainingOutcome.brierMean === null ? 'N/A' : latestTrainingOutcome.brierMean.toFixed(4) }}</p>
      </article>
      <article title="Lower drift is better calibration agreement between predicted and observed frequencies.">
        <p class="text-[var(--text-secondary)]">Calibration Drift</p>
        <p class="font-semibold">{{ latestTrainingOutcome.calibrationDrift === null ? 'N/A' : latestTrainingOutcome.calibrationDrift.toFixed(4) }}</p>
      </article>
      <article title="Lower-bound AUC observed across folds for the latest completed run.">
        <p class="text-[var(--text-secondary)]">Worst-fold AUC</p>
        <p class="font-semibold">{{ latestTrainingOutcome.aucMin === null ? 'N/A' : latestTrainingOutcome.aucMin.toFixed(3) }}</p>
      </article>
    </section>

    <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm" v-if="mode === 'advanced'">
      <h3 class="mb-3 text-sm font-semibold">Advanced Options</h3>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label class="space-y-1 text-sm" title="Controls which historical slice is used for training extraction.">
          <span class="text-[var(--text-secondary)]">Dataset profile</span>
          <select v-model="config.datasetProfile" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
            <option value="rolling-90d">rolling-90d</option>
            <option value="rolling-180d">rolling-180d</option>
            <option value="event-focused">event-focused</option>
          </select>
        </label>
        <label class="space-y-1 text-sm" title="Prediction horizon in bars for target labeling and evaluation.">
          <span class="text-[var(--text-secondary)]">Horizon (bars)</span>
          <input v-model.number="config.horizonBars" type="number" min="1" max="24" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
        </label>
        <label class="space-y-1 text-sm" title="Time-series cross-validation fold count used for validation.">
          <span class="text-[var(--text-secondary)]">CV folds</span>
          <input v-model.number="config.cvFolds" type="number" min="3" max="10" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
        </label>
        <label class="space-y-1 text-sm" title="Probability calibration method for converting raw model scores into calibrated probabilities.">
          <span class="text-[var(--text-secondary)]">Calibration</span>
          <select v-model="config.calibration" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
            <option value="isotonic">isotonic</option>
            <option value="platt">platt</option>
            <option value="none">none</option>
          </select>
        </label>
      </div>
      <p class="mt-2 text-xs text-[var(--text-secondary)]">
        Advanced settings are persisted when you click Save Strategy Settings and reused as default launch parameters.
      </p>
      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4 text-sm">
        <label class="check-row"><input v-model="config.includeMacro" type="checkbox" /><span class="check-label">Include macro features</span></label>
        <label class="check-row"><input v-model="config.includeNewsWindows" type="checkbox" /><span class="check-label">Include news windows</span></label>
        <label class="check-row"><input v-model="config.includeSessionFeatures" type="checkbox" /><span class="check-label">Include session features</span></label>
        <label class="check-row"><input v-model="config.enableClassWeights" type="checkbox" /><span class="check-label">Enable class weights</span></label>
      </div>
    </section>

    <div id="training-diagnostics-section" class="grid gap-4 xl:grid-cols-2">
      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h3 class="mb-2 text-sm font-semibold">ROC Curve</h3>
        <p class="mb-2 text-xs text-[var(--text-secondary)]">Threshold discrimination quality from latest completed training session.</p>
        <p v-if="!latestDiagnostics || latestDiagnostics.rocCurve.length === 0" class="text-sm text-[var(--text-secondary)]">No ROC diagnostics available yet.</p>
        <div v-else class="h-72 overflow-hidden">
          <VChart :option="rocCurveOption" autoresize class="h-full w-full" />
        </div>
      </section>

      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h3 class="mb-2 text-sm font-semibold">Precision-Recall Curve</h3>
        <p class="mb-2 text-xs text-[var(--text-secondary)]">Class precision trade-off by recall from latest completed training session.</p>
        <p v-if="!latestDiagnostics || latestDiagnostics.prCurve.length === 0" class="text-sm text-[var(--text-secondary)]">No PR diagnostics available yet.</p>
        <div v-else class="h-72 overflow-hidden">
          <VChart :option="prCurveOption" autoresize class="h-full w-full" />
        </div>
      </section>
    </div>

    <div class="grid gap-4 xl:grid-cols-2">
      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h3 class="mb-2 text-sm font-semibold">Calibration Reliability Bins</h3>
        <p class="mb-2 text-xs text-[var(--text-secondary)]">Predicted vs observed rates by probability bucket.</p>
        <p v-if="!latestDiagnostics || latestDiagnostics.calibrationBins.length === 0" class="text-sm text-[var(--text-secondary)]">No calibration diagnostics available yet.</p>
        <div v-else class="h-72 overflow-hidden">
          <VChart :option="calibrationOption" autoresize class="h-full w-full" />
        </div>
      </section>

      <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h3 class="mb-2 text-sm font-semibold">Feature Importance</h3>
        <p class="mb-2 text-xs text-[var(--text-secondary)]">Normalized feature contribution from the latest completed training session.</p>
        <p v-if="!latestDiagnostics || latestDiagnostics.featureImportance.length === 0" class="text-sm text-[var(--text-secondary)]">No feature-importance diagnostics available yet.</p>
        <div v-else class="h-72 overflow-hidden">
          <VChart :option="featureImportanceOption" autoresize class="h-full w-full" />
        </div>
      </section>
    </div>

    <section id="training-sessions-section" class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Confusion Matrix</h3>
      <p class="mb-2 text-xs text-[var(--text-secondary)]">Classification outcomes at threshold {{ latestDiagnostics?.confusionMatrix.threshold.toFixed(2) ?? 'N/A' }}.</p>
      <p v-if="!latestDiagnostics" class="text-sm text-[var(--text-secondary)]">No confusion-matrix diagnostics available yet.</p>
      <div v-else class="overflow-x-auto">
        <table class="min-w-[420px] text-left text-sm">
          <thead class="text-[var(--text-secondary)]">
            <tr>
              <th class="py-2 pr-4">Actual / Predicted</th>
              <th class="py-2 pr-4">{{ latestDiagnostics.confusionMatrix.labels[0] }}</th>
              <th class="py-2 pr-4">{{ latestDiagnostics.confusionMatrix.labels[1] }}</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-t border-[var(--border-subtle)]">
              <td class="py-2 pr-4 font-semibold">{{ latestDiagnostics.confusionMatrix.labels[0] }}</td>
              <td class="py-2 pr-4">{{ latestDiagnostics.confusionMatrix.matrix[0][0] }}</td>
              <td class="py-2 pr-4">{{ latestDiagnostics.confusionMatrix.matrix[0][1] }}</td>
            </tr>
            <tr class="border-t border-[var(--border-subtle)]">
              <td class="py-2 pr-4 font-semibold">{{ latestDiagnostics.confusionMatrix.labels[1] }}</td>
              <td class="py-2 pr-4">{{ latestDiagnostics.confusionMatrix.matrix[1][0] }}</td>
              <td class="py-2 pr-4">{{ latestDiagnostics.confusionMatrix.matrix[1][1] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
      <h3 class="mb-2 text-sm font-semibold">Training Sessions and Timeline</h3>
      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="text-[var(--text-secondary)]">
            <tr>
              <th class="py-2 pr-4">Run ID</th>
              <th class="py-2 pr-4">State</th>
              <th class="py-2 pr-4">Dataset</th>
              <th class="py-2 pr-4">Model</th>
              <th class="py-2 pr-4">AUC</th>
              <th class="py-2 pr-4">Brier</th>
              <th class="py-2 pr-4">Created</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="trainingRuns.length === 0" class="border-t border-[var(--border-subtle)]">
              <td colspan="8" class="py-3 text-center text-[var(--text-secondary)]">No recorded training sessions yet.</td>
            </tr>
            <tr v-for="run in trainingRuns" :key="run.id" class="border-t border-[var(--border-subtle)]">
              <td class="py-2 pr-4 font-semibold">{{ run.trainingRunId }}</td>
              <td class="py-2 pr-4">{{ run.status }}</td>
              <td class="py-2 pr-4">{{ run.datasetVersion ?? 'N/A' }}</td>
              <td class="py-2 pr-4">{{ run.modelVersion ?? 'N/A' }}</td>
              <td class="py-2 pr-4">{{ getRunOutcomeMetric(run, 'aucMean') === null ? 'N/A' : getRunOutcomeMetric(run, 'aucMean')?.toFixed(3) }}</td>
              <td class="py-2 pr-4">{{ getRunOutcomeMetric(run, 'brierMean') === null ? 'N/A' : getRunOutcomeMetric(run, 'brierMean')?.toFixed(4) }}</td>
              <td class="py-2 pr-4">{{ run.createdAt }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div
      v-if="showTrainingWizard"
      class="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      @click.self="closeTrainingWizard"
    >
      <article class="max-h-[90vh] w-full max-w-4xl overflow-auto rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-xl" aria-label="Training Wizard">
        <div class="mb-3 flex items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-semibold">Training Wizard</h3>
            <p class="text-xs text-[var(--text-secondary)]">Step {{ wizardStep }} of {{ wizardSteps.length }}: {{ wizardStepState.currentTitle }}</p>
          </div>
          <button class="rounded border border-[var(--border-subtle)] px-2 py-1 text-sm" @click="closeTrainingWizard">Close</button>
        </div>

        <div class="mb-4 h-2 overflow-hidden rounded bg-[var(--bg-elevated)]">
          <div class="h-full bg-[var(--accent-info)] transition-all duration-150" :style="{ width: `${wizardProgressPercent}%` }" />
        </div>

        <div class="mb-4 grid gap-2 sm:grid-cols-6">
          <div
            v-for="step in wizardSteps"
            :key="step.id"
            class="rounded border px-2 py-2 text-center text-xs"
            :class="
              step.id === wizardStep
                ? 'border-[var(--accent-info)] bg-[color:color-mix(in_srgb,var(--accent-info),transparent_88%)]'
                : step.id < wizardStep
                  ? 'border-[var(--accent-success)] bg-[color:color-mix(in_srgb,var(--accent-success),transparent_90%)]'
                  : 'border-[var(--border-subtle)]'
            "
          >
            <p class="font-semibold">{{ step.id }}</p>
            <p class="text-[var(--text-secondary)]">{{ step.title }}</p>
          </div>
        </div>

        <section v-if="wizardStep === 1" class="space-y-4">
          <h4 class="text-sm font-semibold">Choose Workflow and Preset</h4>
          <p class="text-xs text-[var(--text-secondary)]">
            Start with an operator-friendly mode and preset. You can still override every parameter in later steps.
          </p>
          <div class="grid gap-3 md:grid-cols-2">
            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">Strategy ID</span>
              <input :value="strategyRuntime.strategyId" disabled class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
            </label>
            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">Strategy Version</span>
              <input :value="strategyRuntime.strategyVersion" disabled class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
            </label>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              class="rounded px-3 py-1 text-sm"
              :class="mode === 'easy' ? 'bg-[var(--accent-info)] text-white' : 'bg-[var(--bg-elevated)]'"
              @click="mode = 'easy'"
            >
              Easy Mode
            </button>
            <button
              class="rounded px-3 py-1 text-sm"
              :class="mode === 'advanced' ? 'bg-[var(--accent-info)] text-white' : 'bg-[var(--bg-elevated)]'"
              @click="mode = 'advanced'"
            >
              Advanced Mode
            </button>
          </div>

          <div class="grid gap-3 md:grid-cols-3">
            <button
              v-for="preset in presets"
              :key="`wizard-${preset.name}`"
              class="rounded-lg border border-[var(--border-subtle)] p-3 text-left"
              :class="selectedPreset === preset.name ? 'bg-[color:color-mix(in_srgb,var(--accent-info),transparent_88%)]' : 'bg-[var(--bg-surface)]'"
              @click="selectedPreset = preset.name"
            >
              <p class="font-semibold">{{ preset.name }}</p>
              <p class="text-xs text-[var(--text-secondary)]">Run time {{ preset.runtime }}</p>
              <p class="mt-1 text-xs text-[var(--text-secondary)]">{{ preset.notes }}</p>
            </button>
          </div>
        </section>

        <section v-else-if="wizardStep === 2" class="space-y-4">
          <h4 class="text-sm font-semibold">Data and Validation Parameters</h4>
          <p class="text-xs text-[var(--text-secondary)]">
            Define the data slice, target horizon, cross-validation depth, and calibration policy used during training.
          </p>
          <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">Dataset profile</span>
              <select v-model="config.datasetProfile" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
                <option value="rolling-90d">rolling-90d</option>
                <option value="rolling-180d">rolling-180d</option>
                <option value="event-focused">event-focused</option>
              </select>
            </label>

            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">Horizon (bars)</span>
              <input v-model.number="config.horizonBars" type="number" min="1" max="64" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
            </label>

            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">CV folds</span>
              <input v-model.number="config.cvFolds" type="number" min="2" max="20" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
            </label>

            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">Calibration</span>
              <select v-model="config.calibration" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
                <option value="isotonic">isotonic</option>
                <option value="platt">platt</option>
                <option value="none">none</option>
              </select>
            </label>

            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">Decision threshold</span>
              <input v-model.number="config.threshold" type="number" min="0.01" max="1" step="0.01" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
            </label>
          </div>
        </section>

        <section v-else-if="wizardStep === 3" class="space-y-4">
          <h4 class="text-sm font-semibold">Feature and Label Toggles</h4>
          <p class="text-xs text-[var(--text-secondary)]">
            Enable or disable optional feature families and weighting behavior before model fitting.
          </p>
          <div class="grid gap-3 md:grid-cols-2">
            <label class="check-row"><input v-model="config.includeMacro" type="checkbox" /><span class="check-label">Include macro features</span></label>
            <label class="check-row"><input v-model="config.includeNewsWindows" type="checkbox" /><span class="check-label">Include news windows</span></label>
            <label class="check-row"><input v-model="config.includeSessionFeatures" type="checkbox" /><span class="check-label">Include session features</span></label>
            <label class="check-row"><input v-model="config.enableClassWeights" type="checkbox" /><span class="check-label">Enable class weights</span></label>
          </div>
        </section>

        <section v-else-if="wizardStep === 4" class="space-y-4">
          <h4 class="text-sm font-semibold">AI Runtime Policy Parameters</h4>
          <p class="text-xs text-[var(--text-secondary)]">
            Configure production gating behavior so live decision policy remains synchronized with training assumptions.
          </p>
          <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">AI full threshold</span>
              <input v-model.number="strategyRuntime.aiThresholdFull" type="number" min="0.01" max="1" step="0.01" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
            </label>

            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">AI half threshold</span>
              <input v-model.number="strategyRuntime.aiThresholdHalf" type="number" min="0.01" max="1" step="0.01" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1" />
            </label>

            <label class="space-y-1 text-sm">
              <span class="text-[var(--text-secondary)]">Risk profile</span>
              <select v-model="strategyRuntime.riskProfile" class="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1">
                <option value="conservative">conservative</option>
                <option value="balanced">balanced</option>
                <option value="active">active</option>
              </select>
            </label>

            <label class="check-row mt-6">
              <input v-model="strategyRuntime.aiMandatory" type="checkbox" />
              <span class="check-label">AI mandatory mode</span>
            </label>
          </div>
        </section>

        <section v-else-if="wizardStep === 5" class="space-y-4">
          <h4 class="text-sm font-semibold">Review and Launch</h4>
          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4 text-sm">
            <article class="rounded border border-[var(--border-subtle)] p-2">
              <p class="text-[var(--text-secondary)]">Mode</p>
              <p class="font-semibold">{{ mode }}</p>
            </article>
            <article class="rounded border border-[var(--border-subtle)] p-2">
              <p class="text-[var(--text-secondary)]">Preset</p>
              <p class="font-semibold">{{ selectedPreset }}</p>
            </article>
            <article class="rounded border border-[var(--border-subtle)] p-2">
              <p class="text-[var(--text-secondary)]">Dataset</p>
              <p class="font-semibold">{{ config.datasetProfile }}</p>
            </article>
            <article class="rounded border border-[var(--border-subtle)] p-2">
              <p class="text-[var(--text-secondary)]">Threshold</p>
              <p class="font-semibold">{{ config.threshold.toFixed(2) }}</p>
            </article>
            <article class="rounded border border-[var(--border-subtle)] p-2">
              <p class="text-[var(--text-secondary)]">CV folds</p>
              <p class="font-semibold">{{ config.cvFolds }}</p>
            </article>
            <article class="rounded border border-[var(--border-subtle)] p-2">
              <p class="text-[var(--text-secondary)]">Horizon</p>
              <p class="font-semibold">{{ config.horizonBars }} bars</p>
            </article>
            <article class="rounded border border-[var(--border-subtle)] p-2">
              <p class="text-[var(--text-secondary)]">AI thresholds</p>
              <p class="font-semibold">half {{ strategyRuntime.aiThresholdHalf.toFixed(2) }} / full {{ strategyRuntime.aiThresholdFull.toFixed(2) }}</p>
            </article>
            <article class="rounded border border-[var(--border-subtle)] p-2">
              <p class="text-[var(--text-secondary)]">Estimated runtime</p>
              <p class="font-semibold">{{ launchSummary.runtime }}</p>
            </article>
          </div>
          <p class="text-xs text-[var(--text-secondary)]">Launching from wizard will save strategy settings first, then start training with the selected configuration.</p>
        </section>

        <section v-else class="space-y-4">
          <h4 class="text-sm font-semibold">Training Launched Successfully</h4>
          <div class="rounded-lg border border-[var(--accent-success)] bg-[color:color-mix(in_srgb,var(--accent-success),transparent_90%)] p-3 text-sm">
            <p class="font-semibold">Run {{ wizardLaunchedRunId || 'N/A' }} is now recorded.</p>
            <p class="mt-1 text-[var(--text-secondary)]">Use the quick actions below to inspect diagnostics and timeline evidence for this session.</p>
          </div>

          <div class="grid gap-2 sm:grid-cols-2">
            <button
              class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-sm font-semibold"
              @click="jumpToStudioSection('training-diagnostics-section')"
            >
              View Diagnostics Panels
            </button>
            <button
              class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-sm font-semibold"
              @click="jumpToStudioSection('training-sessions-section')"
            >
              View Training Timeline
            </button>
          </div>
        </section>

        <p v-if="wizardError" class="mt-3 text-sm text-[var(--accent-danger)]">{{ wizardError }}</p>

        <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
          <button
            class="rounded border border-[var(--border-subtle)] px-3 py-2 text-sm disabled:opacity-60"
            :disabled="wizardStepState.isFirst || wizardSavingAndLaunching"
            @click="wizardPreviousStep"
          >
            Previous
          </button>

          <div class="flex flex-wrap items-center gap-2">
            <button class="rounded border border-[var(--border-subtle)] px-3 py-2 text-sm" @click="closeTrainingWizard">Cancel</button>
            <button
              v-if="wizardStep < 5"
              class="rounded bg-[var(--accent-info)] px-3 py-2 text-sm font-semibold text-white"
              :disabled="wizardSavingAndLaunching"
              @click="wizardNextStep"
            >
              Next
            </button>
            <button
              v-else-if="wizardStep === 5"
              class="rounded bg-[var(--accent-success)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
              :disabled="wizardSavingAndLaunching || strategyConfigSaving || trainingLoading"
              @click="wizardSaveAndLaunch"
            >
              {{ wizardSavingAndLaunching ? 'Saving and Launching...' : 'Save Settings and Launch' }}
            </button>
            <button
              v-else
              class="rounded bg-[var(--accent-success)] px-3 py-2 text-sm font-semibold text-white"
              @click="closeTrainingWizard"
            >
              Done
            </button>
          </div>
        </div>
      </article>
    </div>

    <div
      v-if="showTrainingGuide"
      class="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
    >
      <article class="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-xl">
        <div class="mb-3 flex items-center justify-between gap-3">
          <h3 class="text-base font-semibold">Training Studio Narrative Guide</h3>
          <button class="rounded border border-[var(--border-subtle)] px-2 py-1 text-sm" @click="closeTrainingGuide">Close</button>
        </div>
        <div class="space-y-3 text-sm text-[var(--text-secondary)]">
          <p>
            Easy Mode is the fastest path and uses recommended defaults. Advanced Mode exposes full control over dataset, label horizon,
            cross-validation, calibration, and feature toggles.
          </p>
          <p>
            Save Strategy Settings persists AI threshold and training defaults into the backend. These values are used by /signal and by future
            launch defaults so operators and runtime stay synchronized.
          </p>
          <p>
            Launch Training Run records a new training session and stores achieved metrics. Use the Training Sessions table and metric cards to
            compare sessions before promoting new model versions.
          </p>
          <p>
            Diagnostics panels now visualize confusion matrix, ROC, precision-recall, calibration reliability bins, and feature importance from
            the latest completed training session.
          </p>
          <p>
            Historical Data controls manage provider ingestion into PostgreSQL. Use the preview chart and stored bars table to validate coverage
            before running training jobs.
          </p>
        </div>
      </article>
    </div>
  </div>
</template>
