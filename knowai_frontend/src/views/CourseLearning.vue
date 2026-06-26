<template>
  <div class="learn-page" v-loading="loading">
    <template v-if="!loading && course">
      <!-- Header -->
      <div class="learn-header">
        <button class="learn-back" @click="$router.push('/my-courses')">
          <span class="material-symbols-outlined">arrow_back</span>
        </button>
        <div class="learn-header-info">
          <h1 class="learn-title">{{ course.title }}</h1>
          <span class="learn-meta">{{ totalLessons }} 课时</span>
        </div>
      </div>

      <div class="learn-body">
        <!-- Lesson List Sidebar -->
        <aside class="learn-sidebar">
          <div v-if="chapters.length === 0 && courseVideoUrl" class="learn-chapter">
            <div class="chapter-header" @click="selectCourseVideo">
              <span class="chapter-toggle material-symbols-outlined">smart_display</span>
              <span class="chapter-title">{{ course?.title }}</span>
            </div>
            <div class="chapter-lessons">
              <div
                class="lesson-item"
                :class="{ 'lesson-active': showCourseVideo }"
                @click="selectCourseVideo"
              >
                <span class="lesson-icon">
                  <span class="material-symbols-outlined">play_circle</span>
                </span>
                <span class="lesson-title">课程视频</span>
              </div>
            </div>
          </div>
          <div
            v-for="chapter in chapters"
            :key="chapter.id"
            class="learn-chapter"
          >
            <div class="chapter-header" @click="toggleChapter(chapter.id)">
              <span class="chapter-toggle material-symbols-outlined">{{ expandedChapters.has(chapter.id) ? 'expand_less' : 'expand_more' }}</span>
              <span class="chapter-title">{{ chapter.title }}</span>
              <span class="chapter-count">{{ chapter.lessons.length }} 课</span>
            </div>
            <div v-show="expandedChapters.has(chapter.id)" class="chapter-lessons">
              <div
                v-for="lesson in chapter.lessons"
                :key="lesson.id"
                class="lesson-item"
                :class="{ 'lesson-active': currentLesson?.id === lesson.id, 'lesson-locked': lesson.is_locked }"
                @click="selectLesson(lesson)"
              >
                <span class="lesson-icon">
                  <span v-if="lesson.is_locked" class="material-symbols-outlined">lock</span>
                  <span v-else-if="currentLesson?.id === lesson.id" class="material-symbols-outlined">play_circle</span>
                  <span v-else class="material-symbols-outlined">check_circle</span>
                </span>
                <span class="lesson-title">{{ lesson.title }}</span>
                <span class="lesson-duration">{{ formatDuration(lesson.duration) }}</span>
              </div>
            </div>
          </div>
        </aside>

        <!-- Main Content -->
        <main class="learn-main">
          <template v-if="currentLesson && !currentLesson.is_locked && !showCourseVideo">
            <!-- Video Player -->
            <div class="video-area">
              <div v-if="currentLesson.video_url" class="video-wrapper">
                <video
                  :key="currentLesson.id"
                  :src="currentLesson.video_url"
                  controls
                  class="video-player"
                >
                  您的浏览器不支持视频播放
                </video>
              </div>
              <div v-else class="video-placeholder">
                <span class="material-symbols-outlined">play_circle</span>
                <p>{{ currentLesson.title }}</p>
                <span class="placeholder-hint">视频加载中...</span>
              </div>
            </div>
            <!-- Lesson Info -->
            <div class="lesson-info">
              <h2 class="lesson-title-text">{{ currentLesson.title }}</h2>
              <span class="lesson-duration-text">{{ formatDuration(currentLesson.duration) }}</span>
            </div>
          </template>

          <template v-else-if="courseVideoUrl && (showCourseVideo || (!currentLesson && chapters.length === 0))">
            <!-- Course-level video (no lessons) -->
            <div class="video-area">
              <div class="video-wrapper">
                <video
                  :key="course.id"
                  :src="courseVideoUrl"
                  controls
                  class="video-player"
                >
                  您的浏览器不支持视频播放
                </video>
              </div>
            </div>
            <div class="lesson-info">
              <h2 class="lesson-title-text">{{ course.title }}</h2>
            </div>
          </template>

          <template v-else-if="currentLesson && currentLesson.is_locked">
            <div class="locked-overlay">
              <span class="material-symbols-outlined locked-icon">lock</span>
              <h2>该课时需要购买课程才能观看</h2>
              <p>购买后可解锁全部 {{ totalLessons }} 个课时</p>
              <el-button type="primary" size="large" round @click="$router.push(`/courses/${course.id}`)">
                <span class="material-symbols-outlined" style="font-size:18px">shopping_cart</span> 去购买
              </el-button>
            </div>
          </template>

          <div v-else class="empty-lesson">
            <span class="material-symbols-outlined">menu_book</span>
            <p>请从左侧选择一个课时开始学习</p>
          </div>
        </main>
      </div>
    </template>

    <div v-else-if="!loading && loadError" class="error-state">
      <span class="material-symbols-outlined">error_outline</span>
      <p>{{ loadError }}</p>
      <el-button @click="$router.push('/my-courses')">返回我的学习</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCourse, getCourseChapters, type ChapterData, type LessonData } from '@/api/courses'

const route = useRoute()
const loading = ref(true)
const loadError = ref('')
const course = ref<{ id: number; title: string; video_url?: string | null } | null>(null)
const chapters = ref<ChapterData[]>([])
const currentLesson = ref<LessonData | null>(null)
const expandedChapters = ref(new Set<number>())
const showCourseVideo = ref(false)

const totalLessons = computed(() =>
  chapters.value.reduce((sum, ch) => sum + ch.lessons.length, 0)
)
const courseVideoUrl = computed(() => course.value?.video_url || '')

function selectCourseVideo() {
  showCourseVideo.value = true
  currentLesson.value = null
}

function toggleChapter(id: number) {
  if (expandedChapters.value.has(id)) {
    expandedChapters.value.delete(id)
  } else {
    expandedChapters.value.add(id)
  }
}

function selectLesson(lesson: LessonData) {
  currentLesson.value = lesson
  showCourseVideo.value = false
}

function formatDuration(seconds: number) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s}秒`
  return `${m}分${s > 0 ? s + '秒' : ''}`
}

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id || Number.isNaN(id)) {
    loadError.value = '课程 ID 无效'
    loading.value = false
    return
  }
  try {
    const courseData = await getCourse(id)
    course.value = { id: courseData.id, title: courseData.title, video_url: courseData.video_url }
    const chapterData = await getCourseChapters(id)
    chapters.value = chapterData
    // Expand first chapter by default
    if (chapterData.length > 0) {
      expandedChapters.value.add(chapterData[0].id)
      // Auto-select first unlocked lesson
      const firstUnlocked = chapterData[0].lessons.find(l => !l.is_locked)
      if (firstUnlocked) currentLesson.value = firstUnlocked
    }
  } catch {
    loadError.value = '加载课程内容失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.learn-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--header-height, 64px));
  background: var(--surface-container);
}

/* Header */
.learn-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  background: var(--surface-container-lowest);
  border-bottom: 1px solid var(--outline-variant);
  z-index: 10;
}
.learn-back {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--on-surface);
  padding: 4px;
  display: flex;
  align-items: center;
}
.learn-back .material-symbols-outlined { font-size: 24px; }
.learn-header-info { display: flex; align-items: baseline; gap: 12px; min-width: 0; }
.learn-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--on-surface);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.learn-meta { font-size: 13px; color: var(--on-surface-variant); white-space: nowrap; }

/* Body */
.learn-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebar */
.learn-sidebar {
  width: 340px;
  flex-shrink: 0;
  overflow-y: auto;
  background: var(--surface-container-lowest);
  border-right: 1px solid var(--outline-variant);
}
.learn-chapter { border-bottom: 1px solid var(--outline-variant); }
.chapter-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  cursor: pointer;
  transition: background 0.15s;
  user-select: none;
}
.chapter-header:hover { background: var(--surface-container); }
.chapter-toggle { font-size: 20px; color: var(--on-surface-variant); }
.chapter-title { flex: 1; font-size: 14px; font-weight: 600; color: var(--on-surface); }
.chapter-count { font-size: 12px; color: var(--on-surface-variant); white-space: nowrap; }

.chapter-lessons { border-top: 1px solid var(--outline-variant); }
.lesson-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px 10px 44px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;
}
.lesson-item:hover { background: var(--surface-container); }
.lesson-item.lesson-active { background: var(--primary-fixed); }
.lesson-item.lesson-locked { cursor: not-allowed; opacity: 0.6; }
.lesson-icon { display: flex; align-items: center; }
.lesson-icon .material-symbols-outlined { font-size: 18px; }
.lesson-active .lesson-icon .material-symbols-outlined { color: var(--primary); }
.lesson-item.lesson-locked .lesson-icon .material-symbols-outlined { color: var(--on-surface-variant); }
.lesson-title { flex: 1; color: var(--on-surface); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lesson-active .lesson-title { color: var(--primary); font-weight: 600; }
.lesson-duration { font-size: 12px; color: var(--on-surface-variant); white-space: nowrap; }

/* Main */
.learn-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background: #000; /* video background */
}
@media (prefers-color-scheme: light) {
  .learn-main { background: #1a1a1a; }
}

/* Video */
.video-area {
  position: relative;
  width: 100%;
  background: #000;
}
.video-wrapper { width: 100%; max-width: 1000px; margin: 0 auto; }
.video-player { width: 100%; aspect-ratio: 16 / 9; display: block; background: #000; }
.video-placeholder {
  aspect-ratio: 16 / 9;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: rgba(255,255,255,0.6);
}
.video-placeholder .material-symbols-outlined { font-size: 64px; opacity: 0.5; }
.video-placeholder p { font-size: 16px; margin: 0; }
.placeholder-hint { font-size: 13px; }

/* Lesson Info */
.lesson-info {
  padding: 20px 32px;
  background: var(--surface-container-lowest);
  border-top: 1px solid var(--outline-variant);
}
.lesson-title-text {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 700;
  color: var(--on-surface);
}
.lesson-duration-text { font-size: 13px; color: var(--on-surface-variant); }

/* Locked Overlay */
.locked-overlay {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 24px;
  text-align: center;
  background: var(--surface-container);
}
.locked-icon { font-size: 64px; color: var(--on-surface-variant); opacity: 0.5; }
.locked-overlay h2 { margin: 0; font-size: 20px; color: var(--on-surface); }
.locked-overlay p { margin: 0; font-size: 14px; color: var(--on-surface-variant); }

/* Empty state */
.empty-lesson {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--on-surface-variant);
  background: var(--surface-container);
}
.empty-lesson .material-symbols-outlined { font-size: 64px; opacity: 0.4; }

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 24px;
  color: var(--on-surface-variant);
}
.error-state .material-symbols-outlined { font-size: 64px; opacity: 0.4; }

@media (max-width: 800px) {
  .learn-sidebar { width: 260px; }
}
@media (max-width: 600px) {
  .learn-body { flex-direction: column; }
  .learn-sidebar { width: 100%; max-height: 40vh; border-right: none; border-bottom: 1px solid var(--outline-variant); }
}
</style>
