<template>
  <div class="home-page">
    <!-- Ambient light & wave background -->
    <div class="ambient-bg">
      <div class="ambient-orb ambient-orb-1"></div>
      <div class="ambient-orb ambient-orb-2"></div>
      <div class="ambient-orb ambient-orb-3"></div>
      <div class="wave-layer wave-layer-1"></div>
      <div class="wave-layer wave-layer-2"></div>
    </div>

    <!-- Hero Carousel -->
    <HomeCarousel />

    <!-- Seckill Section -->
    <section v-if="seckillCourses.length" class="section-seckill">
      <div class="container">
        <div class="section-head">
          <div>
            <div class="section-label">
              <span class="material-symbols-outlined">bolt</span> 限时秒杀
            </div>
            <h2>限时秒杀活动</h2>
            <p class="sub">低价精品课正在排队抢购，手慢无</p>
          </div>
          <div class="countdown">
            <span class="cd-label">剩余时间</span>
            <span class="cd-time">{{ countdownStr }}</span>
          </div>
        </div>
        <div class="grid">
          <div v-for="course in seckillCourses" :key="course.id" class="seckill-card">
            <div class="sc-cover">
              <el-image :src="course.cover || ''" fit="cover">
                <template #error>
                  <div class="cover-fallback">
                    <span class="material-symbols-outlined">local_fire_department</span>
                  </div>
                </template>
              </el-image>
              <span class="badge badge-seckill">
                <span class="material-symbols-outlined">local_fire_department</span> 秒杀中
              </span>
            </div>
            <div class="sc-body">
              <h3>{{ course.title }}</h3>
              <div class="sc-price-row">
                <span class="sc-price">¥{{ course.seckill_price || '9.90' }}</span>
                <span class="sc-original">¥{{ originalPrice(course) }}</span>
                <span class="sc-sold">{{ stockLabel(course) }}</span>
              </div>
              <div class="sc-progress">
                <div class="sc-progress-bar" :style="{ width: stockPercent(course) }" />
              </div>
              <div class="sc-time-remaining" v-if="seckillRemaining(course)">
                <span class="material-symbols-outlined" style="font-size:14px">schedule</span>
                {{ seckillRemaining(course) }}
              </div>
              <RouterLink :to="`/courses/${course.id}`" class="sc-btn">
                立即抢购
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Hot Courses Bento Grid -->
    <section class="container">
      <div class="section-head">
        <div>
          <h2>热门课程与智能精选</h2>
          <p class="sub">发现时下最火爆的内容，以及 AI 为您量身定制的专属推荐</p>
        </div>
        <RouterLink to="/courses">查看全部 <span class="material-symbols-outlined">chevron_right</span></RouterLink>
      </div>
      <div class="bento">
        <!-- Featured large card -->
        <div v-if="featured" class="bento-featured">
          <div class="bf-bg">
            <el-image :src="featured.cover || ''" fit="cover" class="bf-img">
              <template #error>
                <div class="cover-fallback">
                  <span class="material-symbols-outlined">auto_awesome</span>
                </div>
              </template>
            </el-image>
            <div class="bf-overlay" />
          </div>
          <div class="bf-content">
            <RouterLink to="/ai-recommend" class="bf-chip ai-glass">
              <span class="material-symbols-outlined">auto_awesome</span> 为您智能推荐
            </RouterLink>
            <h3 class="bf-title">{{ featured.title }}</h3>
            <p class="bf-desc">{{ featured.description || '基于您的兴趣，我们推荐此课程。' }}</p>
            <div class="bf-actions">
              <RouterLink :to="`/courses/${featured.id}`" class="btn-ai">
                立即报名
              </RouterLink>
              <span class="bf-learners">
                <span class="material-symbols-outlined">group</span> {{ featured.learn_count || 0 }} 人学习
              </span>
            </div>
          </div>
        </div>
        <!-- Mini hot cards -->
        <RouterLink
          v-for="(course, index) in hotSliced"
          :key="course.id"
          :to="`/courses/${course.id}`"
          class="bento-mini"
          :class="miniCardClass(index)"
        >
          <FavoriteButton :course-id="course.id" variant="inline" class="bmi-fav" />
          <div class="bmi-top">
            <span class="badge-pill" :class="course.seckill_price ? 'is-seckill' : 'is-hot'">
              {{ course.seckill_price ? '秒杀' : '热门' }}
            </span>
            <span class="material-symbols-outlined">trending_up</span>
          </div>
          <div>
            <h4 class="bmi-title">{{ course.title }}</h4>
            <p class="bmi-sub">{{ (course.description || '').slice(0, 40) }}...</p>
          </div>
          <div class="bmi-footer">
            <span class="bmi-price">
              <template v-if="course.seckill_price">¥{{ course.seckill_price }}</template>
              <template v-else-if="Number(course.skus?.[0]?.price) > 0">¥{{ course.skus?.[0]?.price }}</template>
              <template v-else>免费</template>
            </span>
            <div class="bmi-rating">
              <span class="material-symbols-outlined">star</span>
              {{ course.rating?.toFixed(1) }}
            </div>
          </div>
        </RouterLink>
      </div>
    </section>

    <!-- CTA Banner -->
    <section class="container">
      <div class="cta">
        <div class="cta-text">
          <h2 class="cta-title">准备好开始您的 <span class="ai-gradient-text">AI 引导</span> 之旅了吗？</h2>
          <p class="cta-sub">加入 50,000+ 名学习者，通过学伴的智能课程体系加速您的职业生涯。</p>
          <div class="cta-actions">
            <RouterLink :to="userStore.isLoggedIn ? '/my-courses' : '/login'" class="btn-ai">
              {{ userStore.isLoggedIn ? '继续学习' : '免费开始使用' }}
            </RouterLink>
            <RouterLink to="/courses" class="cta-link">浏览课程 <span class="material-symbols-outlined">arrow_forward</span></RouterLink>
          </div>
        </div>
        <div class="cta-card ai-glass">
          <div class="cta-card-inner">
            <div class="cta-card-avatar">
              <span class="material-symbols-outlined">smart_toy</span>
            </div>
            <div>
              <p class="cta-card-title">学伴</p>
              <p class="cta-card-status">正在生成学习路径...</p>
            </div>
          </div>
          <div class="cta-bars">
            <div class="cta-bar"><div class="cta-bar-fill" style="width:66%" /></div>
            <div class="cta-bar"><div class="cta-bar-fill" style="width:45%" /></div>
          </div>
          <p class="cta-card-tip">"根据您的目标，我建议从机器学习基础开始学习。"</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import HomeCarousel from '@/components/HomeCarousel.vue'
import FavoriteButton from '@/components/FavoriteButton.vue'
import { listCourses, listSeckillCourses, type Course } from '@/api/courses'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const courses = ref<Course[]>([])
const totalCourses = ref(0)
const seckillCourses = ref<Course[]>([])

const featured = computed(() => courses.value[0] || null)
const hotSliced = computed(() => courses.value.slice(1, 5))

const seckillEndTime = computed(() => {
  const endTimes = seckillCourses.value
    .map((c) => (c.seckill_end_time ? new Date(c.seckill_end_time).getTime() : 0))
    .filter((t) => t > 0)
  return endTimes.length ? Math.min(...endTimes) : 0
})

const stats = computed(() => {
  const totalLearners = courses.value.reduce((s, c) => s + (c.learn_count || 0), 0)
  const rated = courses.value.filter((c) => c.rating > 0)
  const avgRating = rated.length
    ? (rated.reduce((s, c) => s + c.rating, 0) / rated.length).toFixed(1)
    : '5.0'
  return {
    totalCourses: totalCourses.value || courses.value.length,
    totalLearners: totalLearners > 1000 ? `${Math.floor(totalLearners / 1000)}K` : totalLearners,
    avgRating,
  }
})

function miniCardClass(index: number) {
  return index === 1 ? 'bmi-accent' : ''
}

function originalPrice(course: Course): string {
  const skus = course.skus || []
  const paid = skus.filter((s) => Number(s.price) > 0)
  const pool = paid.length ? paid : skus
  if (!pool.length) return '¥199.00'
  const max = pool.reduce((m, s) => (Number(s.price) > Number(m) ? s.price : m), pool[0].price)
  return `¥${max}`
}

function minStock(course: Course): number {
  const paid = (course.skus || []).filter((s) => Number(s.price) > 0)
  if (!paid.length) return 999
  return Math.min(...paid.map((s) => s.stock))
}

function stockLabel(course: Course): string {
  const stock = minStock(course)
  if (stock <= 10) return `仅剩 ${stock} 份`
  if (stock <= 50) return '即将售罄'
  if (stock <= 200) return '火热抢购中'
  return '限时秒杀'
}

function stockPercent(course: Course): string {
  const stock = minStock(course)
  const pct = Math.min(95, Math.max(10, 100 - stock / 10))
  return `${pct}%`
}

function seckillRemaining(course: Course): string {
  if (!course.seckill_end_time) return ''
  const diff = new Date(course.seckill_end_time).getTime() - Date.now()
  if (diff <= 0) return ''
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  if (h > 0) return `${h}:${pad(m)}:${pad(s)}`
  return `${pad(m)}:${pad(s)}`
}

const countdownStr = ref('')
function updateCountdown() {
  const now = Date.now()
  // Real-time filter expired courses
  seckillCourses.value = seckillCourses.value.filter((c) => {
    if (!c.seckill_end_time) return true
    return new Date(c.seckill_end_time).getTime() > now
  })
  const target = seckillEndTime.value
  if (!target) {
    countdownStr.value = '00:00:00'
    return
  }
  const diff = Math.max(0, target - Date.now())
  const days = Math.floor(diff / 86400000)
  const h = Math.floor((diff % 86400000) / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  countdownStr.value = days > 0 ? `${days}天 ${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(h)}:${pad(m)}:${pad(s)}`
}

let countdownTimer: ReturnType<typeof setInterval> | null = null
let seckillRefreshTimer: ReturnType<typeof setInterval> | null = null

async function fetchSeckillCourses() {
  try {
    const now = Date.now()
    const courses = await listSeckillCourses()
    seckillCourses.value = courses.filter((c) => {
      if (!c.seckill_price) return false
      if (c.seckill_end_time && new Date(c.seckill_end_time).getTime() <= now) return false
      return true
    })
  } catch {
    // seckill display is optional
  }
}

onMounted(async () => {
  try {
    const result = await listCourses({ page: 1, page_size: 8 })
    courses.value = result.items
    totalCourses.value = result.total
  } catch {
    courses.value = []
  }
  await fetchSeckillCourses()
  updateCountdown()
  countdownTimer = setInterval(updateCountdown, 1000)
  // Refresh seckill list every 15s to remove expired courses
  seckillRefreshTimer = setInterval(fetchSeckillCourses, 15000)
})

onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  if (seckillRefreshTimer) {
    clearInterval(seckillRefreshTimer)
    seckillRefreshTimer = null
  }
})
</script>

<style scoped>
/* ——— Seckill ——— */
.section-seckill {
  background: var(--surface-container-low);
  padding: 48px 0;
  position: relative;
  overflow: hidden;
}
.section-seckill::before {
  content: '';
  position: absolute;
  top: -40%; right: -10%;
  width: 400px; height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 86, 48, 0.08), transparent 70%);
  pointer-events: none;
}
.section-label {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 13px; font-weight: 700; color: var(--danger);
  text-transform: uppercase; letter-spacing: 0.04em;
  margin-bottom: 4px;
  animation: label-glow 2s ease-in-out infinite;
}
@keyframes label-glow {
  0%, 100% { text-shadow: 0 0 0 rgba(255, 86, 48, 0); }
  50% { text-shadow: 0 0 12px rgba(255, 86, 48, 0.4); }
}
.section-label .material-symbols-outlined { font-size: 18px; animation: bolt-shake 1.5s ease-in-out infinite; }
@keyframes bolt-shake {
  0%, 100% { transform: rotate(0); }
  25% { transform: rotate(-8deg); }
  75% { transform: rotate(8deg); }
}
.countdown {
  display: flex; align-items: center; gap: 12px;
  background: var(--surface-container-lowest);
  padding: 10px 18px;
  border-radius: var(--radius-lg);
  box-shadow: var(--elev-1);
  border: 1px solid var(--outline-variant);
}
.cd-label { font-size: 13px; font-weight: 600; color: var(--on-surface-variant); }
.cd-time {
  font-size: 20px; font-weight: 700;
  font-family: 'SF Mono', Menlo, monospace;
  color: var(--danger);
  font-variant-numeric: tabular-nums;
}

.seckill-card {
  background: var(--surface-container-lowest);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--outline-variant);
  box-shadow: var(--elev-1);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}
.seckill-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  pointer-events: none;
  box-shadow: 0 0 0 0 rgba(255, 86, 48, 0);
  transition: box-shadow 0.3s;
}
.seckill-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--elev-2);
  border-color: var(--danger);
}
.seckill-card:hover::after {
  box-shadow: 0 0 0 3px rgba(255, 86, 48, 0.15);
}
.sc-cover { position: relative; height: 140px; overflow: hidden; }
.sc-cover .el-image { width: 100%; height: 100%; transition: transform 0.5s; }
.seckill-card:hover .sc-cover .el-image { transform: scale(1.08); }
.sc-cover .badge { position: absolute; top: 10px; left: 10px; }
.sc-body { padding: 14px; }
.sc-body h3 { margin: 0 0 10px; font-size: 15px; font-weight: 600; line-height: 1.4; }
.sc-price-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; }
.sc-price { font-size: 22px; font-weight: 800; color: var(--danger); }
.sc-original { font-size: 13px; color: var(--outline); text-decoration: line-through; }
.sc-sold { margin-left: auto; font-size: 12px; color: var(--on-surface-variant); }
.sc-time-remaining { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--danger); font-weight: 600; margin-bottom: 10px; font-variant-numeric: tabular-nums; }
.sc-progress { height: 5px; background: var(--surface-gray); border-radius: 3px; margin-bottom: 12px; overflow: hidden; }
.sc-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--danger), #ff8a65);
  border-radius: 3px;
  position: relative;
  animation: progress-shimmer 2s ease-in-out infinite;
}
@keyframes progress-shimmer {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
.sc-btn {
  display: block; width: 100%; padding: 10px;
  text-align: center;
  background: var(--inverse-surface);
  color: var(--inverse-on-surface);
  border-radius: 10px;
  font-size: 14px; font-weight: 600;
  transition: all 0.2s;
}
.sc-btn:hover { background: var(--danger); color: #fff; transform: scale(1.02); }

/* ——— Bento ——— */
.bento {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  grid-template-rows: 200px 200px;
  gap: 20px;
}
.bento-featured {
  grid-row: 1 / 3;
  position: relative;
  border-radius: var(--radius-xl);
  overflow: hidden;
  border: 1px solid var(--outline-variant);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.bento-featured:hover { transform: translateY(-4px); }
.bf-bg { position: absolute; inset: 0; }
.bf-img { width: 100%; height: 100%; transition: transform 0.7s; }
.bento-featured:hover .bf-img { transform: scale(1.12); }
.bf-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to top, var(--inverse-surface) 0%, transparent 60%);
}
.bf-content {
  position: relative; z-index: 1;
  padding: 28px;
  display: flex; flex-direction: column; justify-content: flex-end;
  height: 100%;
}
.bf-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-full);
  font-size: 12px; font-weight: 600;
  color: #fff;
  background: var(--ai-gradient);
  align-self: flex-start;
  margin-bottom: 14px;
  text-decoration: none;
  transition: all 0.25s ease;
}
.bf-chip:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(101, 84, 192, 0.4); }
@keyframes chip-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(101, 84, 192, 0.5); }
  50% { box-shadow: 0 0 0 8px rgba(101, 84, 192, 0); }
}
.bf-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--inverse-on-surface);
  margin: 0 0 8px;
  letter-spacing: -0.01em;
}
.bf-desc {
  font-size: 14px;
  color: rgba(237, 240, 255, 0.7);
  margin: 0 0 16px;
  max-width: 400px;
  line-height: 1.5;
}
.bf-actions {
  display: flex; align-items: center; gap: 16px;
}
.bf-learners {
  display: flex; align-items: center; gap: 4px;
  font-size: 13px; color: var(--inverse-on-surface);
}
.bf-learners .material-symbols-outlined { font-size: 18px; }

.bento-mini {
  background: var(--surface-container-lowest);
  border-radius: var(--radius-lg);
  padding: 20px;
  border: 1px solid var(--outline-variant);
  box-shadow: var(--elev-1);
  display: flex; flex-direction: column; justify-content: space-between;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
  text-decoration: none;
  color: var(--on-surface);
}
.bento-mini::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--ai-gradient);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.4s ease;
}
.bento-mini:hover {
  transform: translateY(-4px);
  box-shadow: var(--elev-2);
  border-color: var(--primary);
}
.bento-mini:hover::before { transform: scaleX(1); }
.bento-mini.bmi-accent { background: var(--surface-container-lowest); color: var(--on-surface); }
.bmi-fav {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 2;
}
.bmi-top { display: flex; justify-content: space-between; align-items: start; }
.bmi-title { font-size: 18px; font-weight: 600; margin: 12px 0 6px; color: inherit; }
.bmi-sub { font-size: 13px; color: var(--on-surface-variant); margin: 0; }
.bento-mini.bmi-accent .bmi-sub { color: var(--on-surface-variant); opacity: 1; }
.bmi-footer { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; }
.bmi-price { font-size: 18px; font-weight: 700; color: var(--primary); }
.bmi-rating { display: flex; align-items: center; gap: 2px; font-size: 13px; color: var(--on-surface-variant); }
.bmi-rating .material-symbols-outlined { font-size: 16px; color: var(--warning); }

/* ——— CTA ——— */
.cta {
  background: var(--inverse-surface);
  border-radius: var(--radius-2xl);
  padding: 56px;
  display: flex; align-items: center; justify-content: space-between;
  gap: 40px;
  overflow: hidden;
  position: relative;
}
.cta::before {
  content: '';
  position: absolute;
  top: -50%; left: -10%;
  width: 500px; height: 500px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(101, 84, 192, 0.18), transparent 70%);
  animation: cta-glow 8s ease-in-out infinite;
}
@keyframes cta-glow {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(50px, 30px); }
}
.cta-text { position: relative; z-index: 1; max-width: 520px; }
.cta-title {
  font-size: 32px; font-weight: 700; color: var(--inverse-on-surface);
  margin: 0 0 16px; letter-spacing: -0.01em;
}
.cta-sub { font-size: 16px; color: rgba(237, 240, 255, 0.7); margin: 0 0 24px; line-height: 1.6; }
.cta-actions { display: flex; align-items: center; gap: 16px; }
.cta-link {
  color: var(--inverse-on-surface);
  font-weight: 600; font-size: 15px;
  display: inline-flex; align-items: center; gap: 4px;
  transition: opacity 0.2s;
}
.cta-link:hover { opacity: 0.8; }
.cta-link .material-symbols-outlined { font-size: 18px; transition: transform 0.2s; }
.cta-link:hover .material-symbols-outlined { transform: translateX(4px); }

.cta-card { position: relative; z-index: 1; padding: 24px; width: 300px; flex-shrink: 0; }
.cta-card-inner { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.cta-card-avatar {
  width: 40px; height: 40px;
  border-radius: 12px;
  background: var(--primary-container);
  display: flex; align-items: center; justify-content: center;
  color: var(--on-primary-container);
  animation: avatar-float 3s ease-in-out infinite;
}
@keyframes avatar-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
.cta-card-avatar .material-symbols-outlined { font-size: 22px; }
.cta-card-title { margin: 0; font-size: 14px; font-weight: 600; color: var(--on-surface); }
.cta-card-status { margin: 0; font-size: 11px; color: var(--primary); }
.cta-card-status::before {
  content: '';
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--tertiary);
  margin-right: 4px;
  animation: status-blink 1.5s ease-in-out infinite;
}
@keyframes status-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.cta-bars { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.cta-bar { height: 6px; background: var(--surface-gray); border-radius: 3px; overflow: hidden; }
.cta-bar-fill { height: 100%; background: var(--primary); border-radius: 3px; }
.cta-bar-fill::after {
  content: ''; display: block; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
}
.cta-card-tip { font-size: 12px; color: var(--on-surface-variant); margin: 0; line-height: 1.5; }

@media (max-width: 960px) {
  .bento { grid-template-columns: 1fr 1fr; grid-template-rows: auto; }
  .bento-featured { grid-row: auto; min-height: 300px; }
  .cta { flex-direction: column; padding: 40px 24px; }
  .cta-title { font-size: 26px; }
  .cta-card { width: 100%; }
}
@media (max-width: 560px) {
  .bento { grid-template-columns: 1fr; }
}

/* ===== Ambient background (Stitch-style light & wave effects) ===== */
.home-page {
  position: relative;
  min-height: 100vh;
}
.ambient-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}
.ambient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.3;
}
.ambient-orb-1 {
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(101, 84, 192, 0.5), transparent 70%);
  top: -20%; left: -10%;
  animation: ambient-float-1 20s ease-in-out infinite;
}
.ambient-orb-2 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(0, 82, 204, 0.4), transparent 70%);
  bottom: -15%; right: -5%;
  animation: ambient-float-2 24s ease-in-out infinite;
}
.ambient-orb-3 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(171, 71, 188, 0.35), transparent 70%);
  top: 40%; left: 50%;
  animation: ambient-float-3 18s ease-in-out infinite;
}
@keyframes ambient-float-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(80px, 60px) scale(1.1); }
  66% { transform: translate(-40px, 100px) scale(0.95); }
}
@keyframes ambient-float-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-60px, -80px) scale(1.15); }
}
@keyframes ambient-float-3 {
  0%, 100% { transform: translate(0, 0); }
  25% { transform: translate(50px, -40px); }
  50% { transform: translate(-30px, 60px) scale(1.05); }
  75% { transform: translate(-60px, -20px); }
}

/* Wave layers */
.wave-layer {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 200%;
  height: 150px;
  pointer-events: none;
}
.wave-layer-1 {
  background:
    radial-gradient(ellipse 200px 50px at 15% 100%, rgba(101, 84, 192, 0.06), transparent),
    radial-gradient(ellipse 250px 60px at 40% 100%, rgba(0, 82, 204, 0.05), transparent),
    radial-gradient(ellipse 180px 45px at 65% 100%, rgba(171, 71, 188, 0.04), transparent),
    radial-gradient(ellipse 220px 55px at 90% 100%, rgba(0, 150, 136, 0.04), transparent);
  animation: wave-drift 15s linear infinite;
  opacity: 0.7;
}
.wave-layer-2 {
  background:
    radial-gradient(ellipse 180px 45px at 25% 100%, rgba(0, 82, 204, 0.05), transparent),
    radial-gradient(ellipse 200px 50px at 55% 100%, rgba(101, 84, 192, 0.04), transparent),
    radial-gradient(ellipse 160px 40px at 80% 100%, rgba(171, 71, 188, 0.05), transparent);
  animation: wave-drift 20s linear infinite reverse;
  opacity: 0.5;
  height: 120px;
  bottom: -10px;
}
@keyframes wave-drift {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

/* Ensure sections render above ambient bg */
.section-seckill,
.container {
  position: relative;
  z-index: 1;
}
.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--primary-container), var(--secondary-container));
}
.cover-fallback .material-symbols-outlined {
  font-size: 48px;
  opacity: 0.5;
  color: var(--on-primary-container);
}
</style>