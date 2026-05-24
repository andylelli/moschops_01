<script setup lang="ts">
import VChart from 'vue-echarts'
import PageHeader from '../components/PageHeader.vue'

const exposureOption = {
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [
    {
      type: 'pie',
      radius: ['45%', '70%'],
      data: [
        { value: 32, name: 'EURUSD' },
        { value: 24, name: 'GBPUSD' },
        { value: 18, name: 'USDJPY' },
        { value: 14, name: 'XAUUSD' },
        { value: 12, name: 'US30' },
      ],
    },
  ],
}

const budgetOption = {
  tooltip: { trigger: 'axis' },
  grid: { left: 28, right: 12, top: 20, bottom: 20 },
  xAxis: { type: 'category', data: ['Daily cap', 'Weekly cap'] },
  yAxis: { type: 'value', max: 100 },
  series: [
    { type: 'bar', data: [58, 44], barMaxWidth: 42 },
  ],
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader icon="briefcase" title="Portfolio" subtitle="Exposure concentration and budget posture for open risk" />

    <div class="grid gap-4 lg:grid-cols-2">
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Exposure by Symbol</h2>
        <div class="h-64 overflow-hidden">
          <VChart :option="exposureOption" autoresize class="h-full w-full" />
        </div>
      </section>
      <section class="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm">
        <h2 class="mb-2 text-sm font-semibold">Risk Budget Consumption</h2>
        <div class="h-64 overflow-hidden">
          <VChart :option="budgetOption" autoresize class="h-full w-full" />
        </div>
      </section>
    </div>
  </div>
</template>
