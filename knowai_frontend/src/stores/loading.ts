import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useLoadingStore = defineStore('loading', () => {
  const pending = ref(0)
  const loading = computed(() => pending.value > 0)

  function start() {
    pending.value += 1
  }

  function finish() {
    pending.value = Math.max(0, pending.value - 1)
  }

  return { pending, loading, start, finish }
})
