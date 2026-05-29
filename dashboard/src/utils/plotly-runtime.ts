type PlotlyLike = {
  react: (
    root: HTMLDivElement,
    data: unknown[],
    layout?: Record<string, unknown>,
    config?: Record<string, unknown>,
  ) => Promise<void>
  purge: (root: HTMLDivElement) => void
  register: (traces: unknown[]) => void
}

type PlotlyModule = {
  default?: PlotlyLike
} & PlotlyLike

let runtimePromise: Promise<PlotlyLike> | null = null

export function loadPlotlyRuntime(): Promise<PlotlyLike> {
  if (!runtimePromise) {
    runtimePromise = (async () => {
      const [coreModule, scatterModule, barModule, pieModule] = await Promise.all([
        import('plotly.js/lib/core'),
        import('plotly.js/lib/scatter'),
        import('plotly.js/lib/bar'),
        import('plotly.js/lib/pie'),
      ])

      const runtime = (coreModule.default ?? coreModule) as PlotlyModule
      const scatter = scatterModule.default ?? scatterModule
      const bar = barModule.default ?? barModule
      const pie = pieModule.default ?? pieModule

      runtime.register([scatter, bar, pie])
      return runtime
    })()
  }

  return runtimePromise
}