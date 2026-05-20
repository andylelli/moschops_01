<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useUiStore } from './stores/ui'

const ui = useUiStore()
const route = useRoute()
const isMobileMenuOpen = ref(false)

const onKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    isMobileMenuOpen.value = false
  }
}

onMounted(() => {
  ui.applyTheme()
  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  document.body.classList.remove('mobile-menu-open')
})

watch(
  () => route.path,
  () => {
    isMobileMenuOpen.value = false
  },
)

watch(isMobileMenuOpen, (open) => {
  document.body.classList.toggle('mobile-menu-open', open)
})

const navItems = [
  { to: '/overview', label: 'Overview' },
  { to: '/portfolio', label: 'Portfolio' },
  { to: '/trades-signals', label: 'Trades and Signals' },
  { to: '/ai-models', label: 'AI and Models' },
  { to: '/risk-safety', label: 'Risk and Safety' },
  { to: '/system-health', label: 'System Health' },
]
</script>

<template>
  <div class="min-h-screen overflow-x-hidden bg-[var(--bg-base)] text-[var(--text-primary)]">
    <div
      v-if="isMobileMenuOpen"
      class="fixed inset-0 z-40 bg-black/45 md:hidden"
      aria-hidden="true"
      @click="isMobileMenuOpen = false"
    />

    <aside
      class="mobile-panel-pad fixed left-0 top-0 z-50 h-full w-[min(85vw,18rem)] border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-xl transition-transform duration-200 md:hidden"
      :class="isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'"
      role="dialog"
      aria-modal="true"
      aria-label="Mobile navigation menu"
    >
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-sm font-semibold">Navigation</h2>
        <button
          class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm"
          aria-label="Close navigation menu"
          @click="isMobileMenuOpen = false"
        >
          Close
        </button>
      </div>
      <nav class="flex flex-col gap-2">
        <RouterLink
          v-for="item in navItems"
          :key="`mobile-${item.to}`"
          :to="item.to"
          class="rounded px-3 py-2 text-sm"
          :class="route.path === item.to ? 'bg-[var(--accent-info)] text-white' : 'bg-[var(--bg-elevated)]'"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>

    <header class="sticky top-0 z-20 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      <div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
        <button
          class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm md:hidden"
          aria-label="Open navigation menu"
          @click="isMobileMenuOpen = true"
        >
          Menu
        </button>
        <h1 class="mr-auto text-lg font-semibold">Moschops Operator Console</h1>
        <span class="rounded border border-[var(--accent-danger)] bg-[color:color-mix(in_srgb,var(--accent-danger),transparent_88%)] px-2 py-1 text-xs">
          Kill Switch: Normal
        </span>
        <select v-model="ui.environment" class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-sm">
          <option value="dev">dev</option>
          <option value="demo">demo</option>
          <option value="pilot">pilot</option>
          <option value="live">live</option>
        </select>
        <button class="rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-1 text-sm" @click="ui.toggleTheme()">
          Theme: {{ ui.theme }}
        </button>
      </div>
      <nav class="mx-auto hidden max-w-7xl gap-2 overflow-auto px-4 pb-3 md:flex">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="rounded px-3 py-2 text-sm whitespace-nowrap"
          :class="route.path === item.to ? 'bg-[var(--accent-info)] text-white' : 'bg-[var(--bg-elevated)]'"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </header>
    <main class="mx-auto max-w-7xl p-4">
      <RouterView />
    </main>
  </div>
</template>
