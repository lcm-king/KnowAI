<template>
  <div class="recommend-page">
    <!-- Hero -->
    <section class="rec-hero">
      <div class="rec-hero-bg" />
      <div class="rec-hero-content">
        <div class="rec-chip">
          <span class="material-symbols-outlined">auto_awesome</span>
          AI 智能推荐
        </div>
        <h1 class="rec-title">告诉我你想学什么</h1>
        <p class="rec-desc">输入你的学习方向、兴趣领域或目标，AI 将为你量身推荐最合适的课程。</p>
        <div class="rec-input-wrap">
          <input
            v-model="inputText"
            class="rec-input"
            placeholder="例如：想学 Python 和人工智能，零基础"
            :disabled="loading"
            @keyup.enter="search"
          />
          <button class="rec-btn" :disabled="!inputText.trim() || loading" @click="search">
            <span class="material-symbols-outlined">{{ loading ? 'hourglass_top' : 'travel_explore' }}</span>
            <span>{{ loading ? 'AI 思考中...' : '智能推荐' }}</span>
          </button>
        </div>
        <div v-if="inputText && !loading" class="rec-goal-wrap">
          <input v-model="goalText" class="rec-goal-input" placeholder="学习目标（可选）如：成为 Python 后端工程师" />
        </div>
      </div>
    </section>

    <!-- Results -->
    <section v-if="results.length" class="rec-results">
      <div class="rec-results-header">
        <h2>
          <span class="material-symbols-outlined">recommend</span>
          为你推荐的课程
        </h2>
        <span class="rec-result-count">共 {{ results.length }} 门</span>
      </div>
      <div class="rec-grid">
        <RouterLink
          v-for="c in results"
          :key="c.id"
          :to="`/courses/${c.id}`"
          class="rec-card"
        >
          <div class="rec-card-cover">
            <el-image :src="c.cover || ''" fit="cover">
              <template #error>
                <div class="rec-card-fallback">
                  <span class="material-symbols-outlined">menu_book</span>
                </div>
              </template>
            </el-image>
          </div>
          <div class="rec-card-body">
            <h3 class="rec-card-title">{{ c.title }}</h3>
            <p class="rec-card-desc">{{ (c.description || '暂无简介').slice(0, 80) }}</p>
            <div class="rec-card-meta">
              <span class="rec-tag">{{ c.category || '通用' }}</span>
              <span class="rec-rating">
                <span class="material-symbols-outlined">star</span>
                {{ c.rating?.toFixed(1) }}
              </span>
              <span class="rec-learners">
                <span class="material-symbols-outlined">group</span>
                {{ c.learn_count || 0 }}
              </span>
            </div>
          </div>
        </RouterLink>
      </div>
    </section>

    <!-- Empty state -->
    <section v-if="!loading && !results.length && searched" class="rec-empty">
      <span class="material-symbols-outlined">search_off</span>
      <p>没有找到匹配的课程，试试其他关键词吧</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { recommendCourses } from '@/api/ai'
import type { Course } from '@/api/courses'

const inputText = ref('')
const goalText = ref('')
const loading = ref(false)
const results = ref<Course[]>([])
const searched = ref(false)

async function search() {
  const desc = inputText.value.trim()
  if (!desc || loading.value) return
  loading.value = true
  searched.value = true
  try {
    const res = await recommendCourses({
      description: desc,
      goal: goalText.value.trim() || undefined,
      limit: 20,
    })
    results.value = res.items
    if (!res.items.length) {
      ElMessage.info('暂无匹配课程，请调整描述试试')
    }
  } catch {
    ElMessage.error('推荐失败，请稍后再试')
    results.value = []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.recommend-page {
  min-height: calc(100vh - 64px);
  background: var(--surface-container-lowest);
}

/* Hero */
.rec-hero {
  position: relative;
  overflow: hidden;
  padding: 60px var(--gutter);
  text-align: center;
}
.rec-hero-bg {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(160deg, rgba(101, 84, 192, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 30% 40%, rgba(0, 82, 204, 0.06) 0%, transparent 60%),
    radial-gradient(ellipse at 70% 60%, rgba(101, 84, 192, 0.06) 0%, transparent 60%);
  pointer-events: none;
}
.rec-hero-content {
  position: relative;
  z-index: 1;
  max-width: 640px;
  margin: 0 auto;
}
.rec-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  background: var(--primary-container);
  color: var(--on-primary-container);
  margin-bottom: 16px;
}
.rec-chip .material-symbols-outlined { font-size: 16px; }
.rec-title {
  font-size: 36px;
  font-weight: 800;
  color: var(--on-surface);
  margin: 0 0 12px;
  letter-spacing: -0.02em;
}
.rec-desc {
  font-size: 16px;
  color: var(--on-surface-variant);
  margin: 0 0 32px;
  line-height: 1.6;
}
.rec-input-wrap {
  display: flex;
  gap: 8px;
  max-width: 520px;
  margin: 0 auto;
}
.rec-input {
  flex: 1;
  height: 48px;
  padding: 0 16px;
  border-radius: var(--radius);
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  font-size: 15px;
  color: var(--on-surface);
  outline: none;
  transition: border 0.2s;
}
.rec-input:focus { border-color: var(--primary); }
.rec-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 48px;
  padding: 0 24px;
  border-radius: var(--radius);
  background: var(--ai-gradient);
  border: none;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}
.rec-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.rec-btn .material-symbols-outlined { font-size: 20px; }
.rec-goal-wrap {
  max-width: 520px;
  margin: 12px auto 0;
}
.rec-goal-input {
  width: 100%;
  height: 40px;
  padding: 0 16px;
  border-radius: var(--radius);
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  font-size: 14px;
  color: var(--on-surface-variant);
  outline: none;
}
.rec-goal-input:focus { border-color: var(--primary); }

/* Results */
.rec-results {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 40px var(--gutter) 60px;
}
.rec-results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.rec-results-header h2 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 20px;
  color: var(--on-surface);
}
.rec-results-header h2 .material-symbols-outlined { color: var(--primary); }
.rec-result-count {
  font-size: 14px;
  color: var(--on-surface-variant);
}
.rec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}
.rec-card {
  border-radius: var(--radius-lg);
  background: var(--surface-container-low);
  border: 1px solid var(--outline-variant);
  overflow: hidden;
  transition: all 0.25s ease;
  text-decoration: none;
  color: inherit;
}
.rec-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--elev-3);
  border-color: var(--primary-container);
}
.rec-card-cover {
  height: 140px;
  overflow: hidden;
}
.rec-card-cover .el-image { width: 100%; height: 100%; }
.rec-card-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-container-high);
  color: var(--outline);
}
.rec-card-fallback .material-symbols-outlined { font-size: 40px; }
.rec-card-body { padding: 16px; }
.rec-card-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
  color: var(--on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rec-card-desc {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--on-surface-variant);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.rec-card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}
.rec-tag {
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
  background: var(--primary-container);
  color: var(--on-primary-container);
}
.rec-rating,
.rec-learners {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.rec-rating .material-symbols-outlined,
.rec-learners .material-symbols-outlined { font-size: 14px; }
.rec-rating .material-symbols-outlined { color: #ffb400; }

/* Empty */
.rec-empty {
  text-align: center;
  padding: 80px 0;
  color: var(--outline);
}
.rec-empty .material-symbols-outlined { font-size: 56px; }
.rec-empty p { margin: 12px 0 0; font-size: 15px; }
</style>
