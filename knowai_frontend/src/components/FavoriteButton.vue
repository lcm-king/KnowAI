<template>
  <button
    class="fav-icon-btn"
    :class="{ 'is-fav': isFavorited, [variant]: true }"
    :title="isFavorited ? '取消收藏' : '加入收藏'"
    @click.prevent.stop="handleToggle"
  >
    <span class="material-symbols-outlined">{{ isFavorited ? 'bookmark' : 'bookmark_border' }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useFavoritesStore } from '@/stores/favorites'

const props = withDefaults(defineProps<{
  courseId: number
  variant?: 'overlay' | 'inline'
}>(), {
  variant: 'overlay',
})

const userStore = useUserStore()
const favoritesStore = useFavoritesStore()

const isFavorited = computed(() => favoritesStore.has(props.courseId))

async function handleToggle() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录后再收藏')
    return
  }
  // Lazy-load the favorite ID set on first interaction so anonymous users
  // never trigger the /favorites/ids request.
  if (!favoritesStore.loaded) {
    await favoritesStore.load()
  }
  try {
    const res = await favoritesStore.toggle(props.courseId)
    ElMessage.success(res.message)
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { detail?: string }; status?: number }; message?: string }
    if (axiosErr.response?.status !== 401) {
      ElMessage.error(axiosErr.response?.data?.detail || axiosErr.message || '操作失败')
    }
  }
}
</script>

<style scoped>
.fav-icon-btn {
  border: none;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(6px);
}
.fav-icon-btn .material-symbols-outlined { font-size: 18px; }

.fav-icon-btn.overlay {
  width: 34px;
  height: 34px;
  border-radius: 50%;
}
.fav-icon-btn.overlay:hover {
  background: rgba(0, 0, 0, 0.65);
  transform: scale(1.1);
}

.fav-icon-btn.inline {
  width: 32px;
  height: 32px;
  border-radius: var(--radius);
  background: var(--surface-container-low);
  color: var(--on-surface-variant);
}
.fav-icon-btn.inline:hover {
  background: var(--surface-container);
  color: var(--warning);
}

.fav-icon-btn.is-fav {
  background: var(--warning);
  color: #fff;
}
.fav-icon-btn.is-fav.overlay:hover {
  background: var(--danger);
}
</style>
