import { use } from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// Register the renderer and chart primitives used by vue-echarts views.
use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
])
