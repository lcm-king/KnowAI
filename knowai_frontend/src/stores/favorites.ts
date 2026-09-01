import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getFavoriteIds, toggleFavorite } from '@/api/favorites'

/**
 * Holds the current user's favorited course IDs in a single Set.
 *
 * Why: the old FavoriteButton fired one `/favorites/check/{id}` request per card
 * on mount, so a 12-card course list = 12 requests, amplified on every search
 * and pagination. This store loads all favorite IDs once after login and serves
 * every card from memory.
 */
export const useFavoritesStore = defineStore('favorites', () => {
  const ids = ref<Set<number>>(new Set())
  const loaded = ref(false)
  const loading = ref(false)

  function has(courseId: number) {
    return ids.value.has(courseId)
  }

  async function load(force = false) {
    if (loaded.value && !force) return
    if (loading.value) return
    loading.value = true
    try {
      const res = await getFavoriteIds()
      ids.value = new Set(res.ids)
      loaded.value = true
    } catch {
      // leave loaded=false so a later navigation can retry
    } finally {
      loading.value = false
    }
  }

  async function toggle(courseId: number) {
    const res = await toggleFavorite(courseId)
    if (res.favorited) {
      ids.value.add(courseId)
    } else {
      ids.value.delete(courseId)
    }
    // trigger reactivity for Set mutation
    ids.value = new Set(ids.value)
    return res
  }

  function clear() {
    ids.value = new Set()
    loaded.value = false
  }

  return { ids, loaded, loading, has, load, toggle, clear }
})
