<script lang="ts">
import { computed, defineComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type PlotlyLike = {
  react: (
    root: HTMLDivElement,
    data: unknown[],
    layout?: Record<string, unknown>,
    config?: Record<string, unknown>,
  ) => Promise<void>
  purge: (root: HTMLDivElement) => void
}

export default defineComponent({
  name: 'PlotlyPanel',
  props: {
    data: {
      type: Array as () => unknown[],
      required: true,
    },
    layout: {
      type: Object as () => Record<string, unknown>,
      default: () => ({}),
    },
    config: {
      type: Object as () => Record<string, unknown>,
      default: () => ({ responsive: true, displaylogo: false }),
    },
    loading: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: '',
    },
    emptyMessage: {
      type: String,
      default: 'No chart data available.',
    },
    heightClass: {
      type: String,
      default: 'h-72',
    },
  },
  setup(props) {
    const rootEl = ref<HTMLDivElement | null>(null)
    const loadError = ref('')
    const hasData = computed(() => Array.isArray(props.data) && props.data.length > 0)

    let plotlyRuntime: Promise<PlotlyLike> | null = null

    async function renderPlot() {
      if (!rootEl.value || !hasData.value) {
        return
      }

      if (!plotlyRuntime) {
        try {
          const module = await import('../utils/plotly-runtime')
          plotlyRuntime = module.loadPlotlyRuntime()
        } catch (error) {
          loadError.value = error instanceof Error ? error.message : 'Failed to load Plotly runtime.'
          return
        }
      }

      loadError.value = ''
      const runtime = await plotlyRuntime
      await runtime.react(rootEl.value, props.data, props.layout, props.config)
    }

    watch(
      () => [props.data, props.layout, props.config],
      () => {
        void renderPlot()
      },
      { deep: true },
    )

    onMounted(() => {
      void renderPlot()
    })

    onBeforeUnmount(() => {
      if (rootEl.value && plotlyRuntime) {
        void plotlyRuntime.then((runtime) => {
          runtime.purge(rootEl.value as HTMLDivElement)
        })
      }
    })

    return {
      rootEl,
      loadError,
      hasData,
    }
  },
})
</script>

<template>
  <div class="space-y-2">
    <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading chart...</p>
    <p v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</p>
    <p v-else-if="loadError" class="text-sm text-[var(--accent-danger)]">{{ loadError }}</p>
    <p v-else-if="!hasData" class="text-sm text-[var(--text-secondary)]">{{ emptyMessage }}</p>
    <div v-show="!loading && !error && !loadError && hasData" ref="rootEl" :class="['w-full overflow-hidden rounded', heightClass]" />
  </div>
</template>
