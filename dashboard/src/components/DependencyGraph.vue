<script lang="ts">
import { defineComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type CytoscapeLike = {
  (options: Record<string, unknown>): CytoscapeInstance
}

type CytoscapeInstance = {
  destroy: () => void
}

type GraphNode = {
  id: string
  label: string
  type: 'incident' | 'runbook'
  severity?: string
}

type GraphEdge = {
  id: string
  source: string
  target: string
  label?: string
}

function severityColor(severity?: string): string {
  const normalized = (severity ?? '').toUpperCase()

  if (normalized === 'CRITICAL' || normalized === 'ERROR') {
    return '#d92d20'
  }

  if (normalized === 'WARNING' || normalized === 'DEGRADED') {
    return '#dc6803'
  }

  return '#1570ef'
}

export default defineComponent({
  name: 'DependencyGraph',
  props: {
    nodes: {
      type: Array as () => GraphNode[],
      required: true,
    },
    edges: {
      type: Array as () => GraphEdge[],
      required: true,
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
      default: 'No dependency graph data available.',
    },
    heightClass: {
      type: String,
      default: 'h-80',
    },
  },
  setup(props) {
    const rootEl = ref<HTMLDivElement | null>(null)
    const graphError = ref('')

    let cytoscapeFactory: CytoscapeLike | null = null
    let graph: CytoscapeInstance | null = null

    async function renderGraph() {
      if (!rootEl.value || props.nodes.length === 0) {
        return
      }

      if (!cytoscapeFactory) {
        try {
          const module = (await import('cytoscape')) as unknown as { default?: CytoscapeLike } & CytoscapeLike
          cytoscapeFactory = (module.default ?? module) as CytoscapeLike
        } catch (error) {
          graphError.value = error instanceof Error ? error.message : 'Failed to load Cytoscape runtime.'
          return
        }
      }

      graphError.value = ''
      graph?.destroy()

      graph = cytoscapeFactory({
        container: rootEl.value,
        elements: [
          ...props.nodes.map((node) => ({
            data: {
              id: node.id,
              label: node.label,
              type: node.type,
              severity: node.severity ?? '',
              color: node.type === 'runbook' ? '#1570ef' : severityColor(node.severity),
            },
          })),
          ...props.edges.map((edge) => ({
            data: {
              id: edge.id,
              source: edge.source,
              target: edge.target,
              label: edge.label ?? '',
            },
          })),
        ],
        layout: {
          name: 'cose',
          animate: false,
          fit: true,
          padding: 24,
        },
        style: [
          {
            selector: 'node',
            style: {
              label: 'data(label)',
              color: '#e4e7ec',
              'font-size': 11,
              'text-wrap': 'wrap',
              'text-max-width': 120,
              'text-valign': 'center',
              'text-halign': 'center',
              width: 'label',
              height: 'label',
              padding: '12px',
              'background-color': 'data(color)',
              'border-width': 2,
              'border-color': '#d0d5dd',
              shape: 'roundrectangle',
            },
          },
          {
            selector: 'edge',
            style: {
              width: 1.5,
              'line-color': '#98a2b3',
              'curve-style': 'bezier',
              'target-arrow-shape': 'triangle',
              'target-arrow-color': '#98a2b3',
              label: 'data(label)',
              'font-size': 10,
              color: '#667085',
              'text-background-color': '#ffffff',
              'text-background-opacity': 0.85,
              'text-background-padding': '2px',
            },
          },
        ],
      })
    }

    watch(
      () => [props.nodes, props.edges],
      () => {
        void renderGraph()
      },
      { deep: true },
    )

    onMounted(() => {
      void renderGraph()
    })

    onBeforeUnmount(() => {
      graph?.destroy()
    })

    return {
      rootEl,
      graphError,
    }
  },
})
</script>

<template>
  <div class="space-y-2">
    <p v-if="loading" class="text-sm text-[var(--text-secondary)]">Loading dependency graph...</p>
    <p v-else-if="error" class="text-sm text-[var(--accent-danger)]">{{ error }}</p>
    <p v-else-if="graphError" class="text-sm text-[var(--accent-danger)]">{{ graphError }}</p>
    <p v-else-if="nodes.length === 0" class="text-sm text-[var(--text-secondary)]">{{ emptyMessage }}</p>
    <div
      v-show="!loading && !error && !graphError && nodes.length > 0"
      ref="rootEl"
      :class="['w-full overflow-hidden rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)]', heightClass]"
      role="img"
      aria-label="Incident to runbook dependency graph"
    />
  </div>
</template>
