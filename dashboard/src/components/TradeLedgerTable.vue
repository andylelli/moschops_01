<script lang="ts">
import { defineComponent } from 'vue'

export type TradeLedgerRow = {
  id: string
  decisionId: string
  signalId: string
  tradeId: string
  symbol: string
  timeframe: string
  modelVersion: string
  status: string
  capturedAtUtc: string
}

export default defineComponent({
  name: 'TradeLedgerTable',
  props: {
    rows: {
      type: Array as () => TradeLedgerRow[],
      required: true,
    },
  },
})
</script>

<template>
  <div>
    <div class="hidden md:block">
      <div class="overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="text-[var(--text-secondary)]">
            <tr>
              <th class="py-2 pr-3">Decision</th>
              <th class="py-2 pr-3">Signal</th>
              <th class="py-2 pr-3">Trade</th>
              <th class="py-2 pr-3">Symbol</th>
              <th class="py-2 pr-3">TF</th>
              <th class="py-2 pr-3">Model</th>
              <th class="py-2 pr-3">Status</th>
              <th class="py-2 pr-0">Captured UTC</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id" class="border-t border-[var(--border-subtle)]">
              <td class="py-2 pr-3 font-semibold">{{ row.decisionId }}</td>
              <td class="py-2 pr-3">{{ row.signalId }}</td>
              <td class="py-2 pr-3">{{ row.tradeId }}</td>
              <td class="py-2 pr-3">{{ row.symbol }}</td>
              <td class="py-2 pr-3">{{ row.timeframe }}</td>
              <td class="py-2 pr-3">{{ row.modelVersion }}</td>
              <td class="py-2 pr-3">{{ row.status }}</td>
              <td class="py-2 pr-0">{{ row.capturedAtUtc }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <ul class="space-y-2 md:hidden">
      <li v-for="row in rows" :key="`mobile-${row.id}`" class="rounded border border-[var(--border-subtle)] p-3 text-sm">
        <div class="flex items-center justify-between gap-2">
          <p class="font-semibold">{{ row.symbol }} | {{ row.status }}</p>
          <span class="text-xs text-[var(--text-secondary)]">{{ row.timeframe }}</span>
        </div>
        <p class="mt-1 text-xs text-[var(--text-secondary)]">Decision {{ row.decisionId }} | Signal {{ row.signalId }}</p>
        <p class="mt-1 text-xs text-[var(--text-secondary)]">Trade {{ row.tradeId }} | Model {{ row.modelVersion }}</p>
        <p class="mt-1 text-xs text-[var(--text-secondary)]">{{ row.capturedAtUtc }}</p>
      </li>
    </ul>
  </div>
</template>
