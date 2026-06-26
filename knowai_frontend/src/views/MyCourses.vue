<template>
  <div class="my-courses">
    <!-- Header with gradient -->
    <div class="courses-header">
      <div class="courses-header-bg"></div>
      <div class="courses-header-content">
        <div class="courses-header-left">
          <span class="courses-icon">
            <span class="material-symbols-outlined">school</span>
          </span>
          <div>
            <h1 class="courses-title">我的学习</h1>
            <p class="courses-subtitle">持续成长，让知识改变未来</p>
          </div>
        </div>
        <div class="courses-header-right">
          <el-button type="primary" round size="large" @click="$router.push('/courses')">
            <span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle">add_circle</span> 去选课
          </el-button>
        </div>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="courses-stats">
      <div class="stat-card stat-violet">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">menu_book</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ courses.length }}</p>
          <p class="stat-label">已购课程</p>
        </div>
      </div>
      <div class="stat-card stat-cyan">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">speed</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ avgProgress }}%</p>
          <p class="stat-label">平均进度</p>
        </div>
      </div>
      <div class="stat-card stat-indigo">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">check_circle</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ completedCount }}</p>
          <p class="stat-label">已完成</p>
        </div>
      </div>
      <div class="stat-card stat-purple">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">psychology</span></div>
        <div class="stat-info">
          <p class="stat-value">AI</p>
          <p class="stat-label">学习建议</p>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="courses-main">
      <div v-if="loading" class="loading-wrap">
        <span class="material-symbols-outlined spinning">progress_activity</span>
        <p>加载中...</p>
      </div>

      <div v-else-if="!courses.length" class="empty-state">
        <span class="material-symbols-outlined">school</span>
        <p>还没有任何已购课程</p>
        <p class="empty-hint">去浏览精选课程，开启你的学习之旅吧！</p>
        <el-button type="primary" round size="large" @click="$router.push('/courses')">
          <span class="material-symbols-outlined" style="font-size:18px;vertical-align:middle">explore</span> 浏览课程
        </el-button>
      </div>

      <div v-else class="courses-grid">
        <div v-for="course in courses" :key="course.id" class="course-card">
          <div class="cc-cover">
            <div class="cc-cover-icon">
              <span class="material-symbols-outlined">play_circle</span>
            </div>
            <div class="cc-overlay" @click="goToCourse(course.id)">
              <span class="material-symbols-outlined">play_arrow</span>
            </div>
          </div>
          <div class="cc-body">
            <div class="cc-top-row">
              <h3 class="cc-title" @click="goToCourse(course.id)">{{ course.title }}</h3>
              <span class="cc-status" :class="course.progress >= 80 ? 'cc-done' : course.progress >= 30 ? 'cc-learning' : 'cc-new'">
                {{ course.progress >= 80 ? '即将完成' : course.progress >= 30 ? '学习中' : '刚开始' }}
              </span>
            </div>
            <div class="cc-progress">
              <div class="cc-progress-bar">
                <div class="cc-progress-fill" :style="{ width: course.progress + '%', background: progressGradient(course.progress) }" />
              </div>
              <span class="cc-progress-label">{{ course.progress }}%</span>
            </div>
            <div class="cc-footer">
              <span class="cc-meta">
                <template v-if="course.is_trial">
                  <span class="material-symbols-outlined">preview</span>
                  可试看3课时
                </template>
                <template v-else-if="course.expire_date">
                  <span class="material-symbols-outlined">schedule</span>
                  有效期至 {{ formatDate(course.expire_date) }}
                </template>
                <template v-else>
                  <span class="material-symbols-outlined">verified</span>
                  永久有效
                </template>
              </span>
              <el-button size="small" round @click="goToCourse(course.id)">
                <span class="material-symbols-outlined" style="font-size:16px">arrow_forward</span> 继续学习
              </el-button>
            </div>
          </div>
        </div>

        <!-- AI Tip Card -->
        <div class="course-card ai-tip-card">
          <div class="cc-body cc-body-ai">
            <div class="ai-tip-header">
              <span class="material-symbols-outlined">auto_awesome</span>
              <span>AI 学习建议</span>
            </div>
            <p class="ai-tip-text">{{ tipText }}</p>
            <div class="ai-tip-footer">
              <span class="material-symbols-outlined">update</span>
              <span>今日更新</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listMyLearning, type MyLearningCourse } from '@/api/courses'

const router = useRouter()
const courses = ref<MyLearningCourse[]>([])
const loading = ref(true)

const completedCount = computed(() => courses.value.filter(c => c.progress >= 80).length)

const avgProgress = computed(() => {
  if (!courses.value.length) return 0
  const total = courses.value.reduce((s, c) => s + c.progress, 0)
  return Math.round(total / courses.value.length)
})

const tipText = computed(() => {
  if (!courses.value.length) return '还没有学习数据，购买课程后这里会显示个性化建议。'
  const top = [...courses.value].sort((a, b) => b.progress - a.progress)[0]
  if (top.progress >= 80) return `《${top.title}》即将完成，建议本周复盘并进入下一门课程。`
  if (top.progress >= 30) return `《${top.title}》正在稳步推进，保持每日 30 分钟节奏即可。`
  return `建议从《${top.title}》开始，先建立整体知识框架。`
})

function progressGradient(pct: number): string {
  if (pct >= 80) return 'linear-gradient(90deg, #00c853, #69f0ae)'
  if (pct >= 30) return 'linear-gradient(90deg, #7c4dff, #b388ff)'
  return 'linear-gradient(90deg, #18ffff, #84ffff)'
}

function formatDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch {
    return dateStr
  }
}

function goToCourse(id: number) {
  router.push(`/learn/${id}`)
}

async function load() {
  loading.value = true
  try {
    const res = await listMyLearning()
    courses.value = res.items
  } catch {
    courses.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.my-courses {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 32px var(--gutter);
}

/* ===== Header ===== */
.courses-header {
  position: relative;
  border-radius: var(--radius-xl);
  overflow: hidden;
  margin-bottom: 28px;
  padding: 36px 40px;
  background: linear-gradient(135deg, #4a148c 0%, #7b1fa2 50%, #9c27b0 100%);
  color: #fff;
}
.courses-header-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(156, 39, 176, 0.4) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(74, 20, 140, 0.3) 0%, transparent 50%);
  pointer-events: none;
}
.courses-header-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.courses-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.courses-icon {
  font-size: 40px;
  background: rgba(255,255,255,0.15);
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.courses-icon .material-symbols-outlined {
  font-size: 32px;
  color: #fff;
}
.courses-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.01em;
}
.courses-subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: rgba(255,255,255,0.8);
}
.courses-header-right :deep(.el-button) {
  background: rgba(255,255,255,0.2);
  border-color: rgba(255,255,255,0.3);
  color: #fff;
}
.courses-header-right :deep(.el-button:hover) {
  background: rgba(255,255,255,0.3);
}

/* ===== Stats Cards ===== */
.courses-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  box-shadow: var(--elev-1);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--elev-2);
}
.stat-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon-wrap .material-symbols-outlined {
  font-size: 26px;
  color: #fff;
}
.stat-violet .stat-icon-wrap { background: linear-gradient(135deg, #6a1b9a, #8e24aa); }
.stat-cyan .stat-icon-wrap { background: linear-gradient(135deg, #00838f, #00acc1); }
.stat-indigo .stat-icon-wrap { background: linear-gradient(135deg, #283593, #3949ab); }
.stat-purple .stat-icon-wrap { background: linear-gradient(135deg, #7b1fa2, #ab47bc); }

.stat-info { min-width: 0; }
.stat-value {
  margin: 0;
  font-size: 28px;
  font-weight: 800;
  color: var(--on-surface);
  letter-spacing: -0.02em;
}
.stat-label {
  margin: 2px 0 0;
  font-size: 13px;
  color: var(--on-surface-variant);
}

/* ===== Main Content ===== */
.courses-main {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.loading-wrap {
  text-align: center;
  padding: 80px 0;
  color: var(--on-surface-variant);
}
.loading-wrap .material-symbols-outlined {
  font-size: 64px;
  opacity: 0.4;
}
.spinning { animation: spin 1.2s linear infinite !important; }

.empty-state {
  text-align: center;
  padding: 80px 0;
  color: var(--on-surface-variant);
}
.empty-state .material-symbols-outlined {
  font-size: 64px;
  opacity: 0.4;
  display: block;
  margin-bottom: 16px;
}
.empty-state p { margin: 0 0 4px; font-size: 16px; }
.empty-state .empty-hint { font-size: 14px; opacity: 0.7; margin-bottom: 24px; }

/* ===== Grid ===== */
.courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.course-card {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--elev-1);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.course-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--elev-2);
}

.cc-cover {
  position: relative;
  height: 140px;
  background: linear-gradient(135deg, #ede7f6, #e8eaf6);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.cc-cover-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: rgba(123, 31, 162, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}
.cc-cover-icon .material-symbols-outlined {
  font-size: 32px;
  color: #7b1fa2;
}
.cc-overlay {
  position: absolute;
  inset: 0;
  background: rgba(74, 20, 140, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
  cursor: pointer;
}
.cc-overlay:hover { opacity: 1; }
.cc-overlay .material-symbols-outlined {
  font-size: 48px;
  color: #fff;
}

.cc-body { padding: 16px; }
.cc-top-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.cc-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--on-surface);
  cursor: pointer;
  line-height: 1.4;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.cc-title:hover { color: #7b1fa2; }

.cc-status {
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}
.cc-done { background: var(--tertiary-container); color: var(--on-tertiary-container); }
.cc-learning { background: var(--primary-fixed); color: var(--primary); }
.cc-new { background: var(--surface-container); color: var(--on-surface-variant); }

.cc-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.cc-progress-bar {
  flex: 1;
  height: 6px;
  background: var(--surface-container);
  border-radius: 3px;
  overflow: hidden;
}
.cc-progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}
.cc-progress-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--on-surface-variant);
  min-width: 38px;
  text-align: right;
}

.cc-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.cc-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--on-surface-variant);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cc-meta .material-symbols-outlined { font-size: 16px; }

/* ===== AI Tip Card ===== */
.ai-tip-card {
  grid-column: 1 / -1;
  background: linear-gradient(135deg, var(--surface-container-lowest), #ede7f6);
  border-color: #ce93d8;
}
.cc-body-ai { padding: 24px; }
.ai-tip-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #7b1fa2;
  margin-bottom: 12px;
}
.ai-tip-header .material-symbols-outlined { font-size: 22px; }
.ai-tip-text {
  font-size: 14px;
  line-height: 1.7;
  color: var(--on-surface);
  margin: 0 0 14px;
}
.ai-tip-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--on-surface-variant);
}
.ai-tip-footer .material-symbols-outlined { font-size: 16px; }

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 960px) {
  .courses-stats { grid-template-columns: repeat(2, 1fr); }
  .courses-header { padding: 24px 20px; }
  .courses-header-content { flex-direction: column; align-items: flex-start; gap: 12px; }
  .courses-grid { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
}
@media (max-width: 600px) {
  .courses-stats { grid-template-columns: 1fr; }
}
</style>
