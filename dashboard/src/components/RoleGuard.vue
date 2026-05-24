<script lang="ts">
import { computed, defineComponent } from 'vue'

export default defineComponent({
  name: 'RoleGuard',
  props: {
    role: {
      type: String,
      required: true,
    },
    allowedRoles: {
      type: Array as () => string[],
      required: true,
    },
    deniedMessage: {
      type: String,
      default: '',
    },
  },
  setup(props) {
    const isAllowed = computed(() => props.allowedRoles.includes(props.role))
    return {
      isAllowed,
    }
  },
})
</script>

<template>
  <div>
    <slot v-if="isAllowed" />
    <section
      v-else
      class="rounded border border-[var(--accent-warning)] bg-[color:color-mix(in_srgb,var(--accent-warning),transparent_90%)] p-3"
      role="status"
      aria-live="polite"
    >
      <p class="text-sm font-semibold">Action locked for current role.</p>
      <p class="text-xs text-[var(--text-secondary)]">
        {{ deniedMessage ?? 'This control requires elevated permissions.' }}
      </p>
    </section>
  </div>
</template>
