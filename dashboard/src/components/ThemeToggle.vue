<script lang="ts">
import { defineComponent, type PropType } from 'vue'

export default defineComponent({
  name: 'ThemeToggle',
  props: {
    theme: {
      type: String as PropType<'light' | 'dark'>,
      required: true,
    },
  },
  emits: ['toggle'],
})
</script>

<template>
  <button
    type="button"
    class="w-[8.5rem] rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-1 text-center text-sm"
    aria-label="Toggle theme"
    @click="$emit('toggle')"
  >
    <FontAwesomeIcon :icon="['fas', theme === 'dark' ? 'moon' : 'sun']" class="mr-1" aria-hidden="true" />
    {{ theme }}
  </button>
</template>
