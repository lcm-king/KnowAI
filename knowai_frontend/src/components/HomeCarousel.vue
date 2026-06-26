<template>
  <section class="hero">
    <div class="hero-inner">
      <div class="hero-text">
        <div class="hero-chip">
          <span class="material-symbols-outlined">auto_awesome</span> AI 驱动教育
        </div>
        <h1 class="hero-title">
          通过 <span class="ai-gradient-text">个性化 AI</span><br />学习，掌控未来。
        </h1>
        <p class="hero-desc">课程、题库、推荐与智能批改一站式体验，开启通往职业目标的专家级课程路径。</p>
        <div class="hero-actions">
          <RouterLink to="/courses" class="btn-ai">
            浏览全部课程
            <span class="material-symbols-outlined">arrow_forward</span>
          </RouterLink>
          <RouterLink :to="userStore.isLoggedIn ? '/my-courses' : '/login'" class="hero-ghost">
            {{ userStore.isLoggedIn ? '继续学习' : '免费开始使用' }}
          </RouterLink>
        </div>
        <div class="hero-stats">
          <div class="stat-item"><span class="stat-num">500+</span><span class="stat-label">精品课程</span></div>
          <div class="stat-item"><span class="stat-num">50K+</span><span class="stat-label">活跃学员</span></div>
          <div class="stat-item"><span class="stat-num">4.9</span><span class="stat-label">平台评分</span></div>
        </div>
      </div>
      <div class="hero-visual">
        <div class="hero-carousel">
          <transition-group name="slide-fade" tag="div" class="hc-track">
            <div v-for="(c, i) in featured" v-show="i === current" :key="c.id" class="hero-card">
              <div class="hero-card-bg">
                <el-image :src="c.cover || ''" fit="cover" class="hc-cover">
                  <template #error>
                    <div class="hc-cover-fallback"></div>
                  </template>
                </el-image>
                <div class="hero-glow"></div>
                <div class="hero-grid"></div>
                <div class="hc-overlay" />
              </div>
              <div class="hero-card-content">
                <div class="hc-meta">
                  <span class="hc-category">{{ c.category || 'AI 课程' }}</span>
                  <span class="hc-rating">
                    <span class="material-symbols-outlined">star</span>{{ c.rating?.toFixed(1) }}
                  </span>
                </div>
                <h3 class="hc-title">{{ c.title }}</h3>
                <p class="hc-desc">{{ (c.description || 'AI 智能推荐课程').slice(0, 60) }}</p>
                <RouterLink :to="`/courses/${c.id}`" class="hc-cta">
                  立即学习 <span class="material-symbols-outlined">arrow_forward</span>
                </RouterLink>
                <RouterLink to="/ai-recommend" class="hero-card-footer ai-glass">
                  <span class="material-symbols-outlined">auto_awesome</span>
                  <span>AI 智能推荐 · 为你量身定制</span>
                </RouterLink>
              </div>
            </div>
          </transition-group>
          <div class="hc-dots">
            <button
              v-for="(c, i) in featured"
              :key="c.id"
              class="hc-dot"
              :class="{ active: i === current }"
              :aria-label="`切换到课程 ${i + 1}`"
              @click="goto(i)"
            />
          </div>
          <button class="hc-arrow hc-prev" aria-label="上一个" @click="prev">
            <span class="material-symbols-outlined">chevron_left</span>
          </button>
          <button class="hc-arrow hc-next" aria-label="下一个" @click="next">
            <span class="material-symbols-outlined">chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { listCourses, type Course } from '@/api/courses'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const featured = ref<Course[]>([])
const current = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

function next() {
  if (!featured.value.length) return
  current.value = (current.value + 1) % featured.value.length
}
function prev() {
  if (!featured.value.length) return
  current.value = (current.value - 1 + featured.value.length) % featured.value.length
}
function goto(i: number) { current.value = i }

function startAuto() {
  stopAuto()
  timer = setInterval(next, 2000)
}
function stopAuto() {
  if (timer) { clearInterval(timer); timer = null }
}

onMounted(async () => {
  try {
    const res = await listCourses({ page: 1, page_size: 5 })
    featured.value = res.items
    startAuto()
  } catch {
    featured.value = []
  }
})
onUnmounted(stopAuto)
</script>

<style scoped>
.hero {
  width: 100%;
  overflow: hidden;
  background: var(--inverse-surface);
}
.hero-inner {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 0 var(--gutter);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 40px;
  min-height: 540px;
  align-items: center;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: rgba(0, 82, 204, 0.18);
  color: var(--inverse-on-surface);
  margin-bottom: 20px;
  animation: chip-pulse 3s ease-in-out infinite;
}
@keyframes chip-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(101, 84, 192, 0.4); }
  50% { box-shadow: 0 0 0 10px rgba(101, 84, 192, 0); }
}
.hero-chip .material-symbols-outlined { font-size: 16px; }

.hero-title {
  font-size: 48px;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: var(--inverse-on-surface);
  margin: 0 0 16px;
}

.hero-desc {
  font-size: 18px;
  line-height: 1.65;
  color: rgba(237, 240, 255, 0.7);
  max-width: 480px;
  margin: 0 0 28px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
:deep(.btn-ai) {
  padding: 14px 32px;
  font-size: 15px;
  border-radius: var(--radius);
}
.hero-ghost {
  color: var(--inverse-on-surface);
  font-weight: 600;
  font-size: 15px;
  padding: 14px 24px;
  border-radius: var(--radius);
  border: 1px solid rgba(237, 240, 255, 0.2);
  backdrop-filter: blur(8px);
  transition: all 0.2s;
}
.hero-ghost:hover { background: rgba(255, 255, 255, 0.06); }

.hero-stats {
  display: flex;
  gap: 32px;
  margin-top: 40px;
}
.stat-item { display: flex; flex-direction: column; gap: 2px; }
.stat-num {
  font-size: 24px;
  font-weight: 700;
  color: var(--inverse-on-surface);
}
.stat-label {
  font-size: 13px;
  color: rgba(237, 240, 255, 0.55);
}

/* Carousel */
.hero-visual { display: flex; justify-content: center; }
.hero-carousel {
  position: relative;
  width: 440px;
  height: 360px;
}
.hc-track { position: relative; width: 100%; height: 100%; }
.hero-card {
  position: absolute;
  inset: 0;
  border-radius: var(--radius-2xl);
  overflow: hidden;
  box-shadow: var(--elev-3);
}
.hero-card-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(160deg, #0f1b42 0%, #1d2d6b 50%, #0052cc 100%);
}
.hc-cover {
  width: 100%;
  height: 100%;
  opacity: 0.55;
  mix-blend-mode: luminosity;
}
.hero-glow {
  position: absolute;
  top: -40%; right: -20%;
  width: 300px; height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(101, 84, 192, 0.45), transparent 70%);
  animation: glow-drift 8s ease-in-out infinite;
}
@keyframes glow-drift {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-20px, 20px); }
}
.hero-grid {
  position: absolute; inset: 0; opacity: 0.08;
  background-image:
    linear-gradient(rgba(255,255,255,0.15) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.15) 1px, transparent 1px);
  background-size: 40px 40px;
}
.hc-overlay {
  position: absolute; inset: 0;
  background:
    linear-gradient(to top, rgba(15, 27, 66, 0.95) 0%, rgba(15, 27, 66, 0.5) 45%, transparent 75%),
    linear-gradient(135deg, rgba(101, 84, 192, 0.18) 0%, rgba(0, 82, 204, 0.18) 100%);
}
.hero-card-content {
  position: relative; z-index: 1;
  height: 100%;
  display: flex; flex-direction: column; justify-content: flex-end;
  padding: 24px;
  gap: 8px;
}
.hc-meta { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.hc-category {
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 11px; font-weight: 600;
  background: rgba(101, 84, 192, 0.25);
  color: var(--inverse-on-surface);
}
.hc-rating {
  display: inline-flex; align-items: center; gap: 2px;
  font-size: 13px; font-weight: 600;
  color: var(--inverse-on-surface);
}
.hc-rating .material-symbols-outlined { font-size: 14px; color: #ffb400; }
.hc-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--inverse-on-surface);
  margin: 0;
  letter-spacing: -0.01em;
  line-height: 1.3;
}
.hc-desc {
  font-size: 13px;
  color: rgba(237, 240, 255, 0.7);
  margin: 0;
  line-height: 1.5;
}
.hc-cta {
  display: inline-flex; align-items: center; gap: 4px;
  align-self: flex-start;
  margin-top: 6px;
  padding: 8px 16px;
  border-radius: var(--radius);
  background: var(--ai-gradient);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  transition: transform 0.2s;
}
.hc-cta:hover { transform: translateX(3px); }
.hc-cta .material-symbols-outlined { font-size: 16px; }
.hero-card-footer {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  font-size: 12px; font-weight: 600;
  color: #fff;
  margin-top: 12px;
  align-self: flex-start;
  background: var(--ai-gradient);
  opacity: 0.9;
  text-decoration: none;
  transition: all 0.25s ease;
}
.hero-card-footer:hover { opacity: 1; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(101, 84, 192, 0.4); }
.hero-card-footer .material-symbols-outlined { font-size: 16px; }

.hc-dots {
  position: absolute;
  bottom: -28px;
  left: 50%;
  transform: translateX(-50%);
  display: flex; gap: 6px;
}
.hc-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  border: none;
  background: rgba(237, 240, 255, 0.3);
  cursor: pointer;
  transition: all 0.2s;
}
.hc-dot.active {
  width: 24px;
  border-radius: 4px;
  background: var(--ai-gradient);
}
.hc-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 36px; height: 36px;
  border-radius: 50%;
  border: 1px solid rgba(237, 240, 255, 0.2);
  background: rgba(15, 27, 66, 0.4);
  color: var(--inverse-on-surface);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(8px);
  transition: all 0.2s;
  opacity: 0;
}
.hero-carousel:hover .hc-arrow { opacity: 1; }
.hc-arrow:hover { background: var(--ai-gradient); border-color: transparent; }
.hc-arrow .material-symbols-outlined { font-size: 20px; }
.hc-prev { left: -16px; }
.hc-next { right: -16px; }

.slide-fade-enter-active, .slide-fade-leave-active {
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-fade-enter-from { opacity: 0; transform: scale(1.04); }
.slide-fade-leave-to { opacity: 0; transform: scale(0.98); }

@media (max-width: 960px) {
  .hero-inner { grid-template-columns: 1fr; min-height: auto; padding: 48px var(--gutter) 40px; }
  .hero-title { font-size: 34px; }
  .hero-visual { display: none; }
  .hero-stats { gap: 24px; }
}
.hc-cover-fallback {
  width: 100%;
  height: 100%;
}
</style>
