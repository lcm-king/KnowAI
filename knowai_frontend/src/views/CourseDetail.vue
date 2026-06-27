<template>
  <div class="container">
    <div v-if="loading" class="cd-loading">
      <span class="material-symbols-outlined cd-spin">progress_activity</span>
      <p>加载课程中...</p>
    </div>
    <div v-else-if="loadError" class="cd-error">
      <span class="material-symbols-outlined">error_outline</span>
      <p>{{ loadError }}</p>
      <RouterLink to="/courses" class="btn-ai">返回课程列表</RouterLink>
    </div>
    <div v-else-if="course" class="detail-layout">
      <!-- Main content -->
      <div class="main-content">
        <div class="course-header">
          <div class="ch-inline">
            <span v-if="course.seckill_activity_id && !seckillExpired" class="badge-pill is-seckill">
              <span class="material-symbols-outlined">bolt</span> 秒杀
            </span>
            <span v-if="(course.rating || 0) >= 4.7" class="badge-pill is-ai">
              <span class="material-symbols-outlined">auto_awesome</span> AI 推荐
            </span>
          </div>
          <h1 class="ch-title">{{ course.title }}</h1>
          <p class="ch-desc muted">{{ course.description || '暂无简介' }}</p>
          <div class="ch-meta">
            <span class="ch-category">{{ course.category || '综合' }}</span>
            <span class="ch-rate">
              <span class="material-symbols-outlined">star</span>
              {{ course.rating?.toFixed(1) }}
            </span>
            <span>{{ course.learn_count || 0 }} 人学习</span>
            <span>{{ course.total_hours ? course.total_hours + ' 小时' : '暂无时长' }}</span>
          </div>
        </div>

        <!-- SKU Selection -->
        <div class="sku-section">
          <h3 class="section-subtitle">选择版本</h3>
          <div class="sku-options">
            <div
              v-for="sku in skus"
              :key="sku.id"
              class="sku-card"
              :class="{ 'sku-active': selectedSkuId === sku.id }"
              @click="selectedSkuId = sku.id"
            >
              <div class="sku-main">
                <span class="sku-name">{{ sku.sku_name || '标准版' }}</span>
                <span class="sku-price">¥{{ sku.price }}</span>
              </div>
              <div class="sku-sub">
                <span>{{ Number(sku.price) > 0 ? '可永久观看' : (allSkusFree ? '永久免费' : '试看3课时') }}</span>
                <span>库存 {{ sku.stock }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Description -->
        <section class="detail-section">
          <h2 class="section-title">课程介绍</h2>
          <p class="muted desc-text">{{ course.description || '课程内容持续更新中。' }}</p>
        </section>

        <!-- Reviews -->
        <section class="detail-section">
          <h2 class="section-title">课程评价</h2>

          <!-- Review Summary -->
          <div class="review-summary">
            <div class="review-summary-left">
              <span class="review-avg-num">{{ reviewAvg.toFixed(1) }}</span>
              <el-rate v-model="reviewAvg" disabled :max="5" show-score score-template="{value}" />
              <span class="review-count-text">{{ reviewCount }} 条评价</span>
            </div>
          </div>

          <!-- Write Review (logged in + not yet reviewed) -->
          <div v-if="userStore.isLoggedIn && !myReview && !showReviewForm" class="review-write-trigger">
            <button @click="openReviewForm"
              style="padding:6px 16px; min-width:90px; background:#fff; color:#003d9b; border:1px solid #003d9b; border-radius:10px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; font-size:14px; font-weight:600; line-height:1; white-space:nowrap;">
              ✏️ 写评价
            </button>
          </div>

          <div v-if="showReviewForm" class="review-write-box">
            <div class="review-write-header">
              <span class="review-write-label">{{ myReview ? '编辑评价' : '写评价' }}</span>
              <el-rate v-model="reviewForm.rating" :max="5" show-text />
            </div>
            <el-input
              v-model="reviewForm.content"
              type="textarea"
              :rows="3"
              placeholder="分享你的学习体验（可选）"
              maxlength="2000"
              show-word-limit
            />
            <div class="review-write-actions">
              <el-button @click="cancelReviewForm">取消</el-button>
              <el-button type="primary" :loading="reviewSubmitting" @click="submitReview">
                {{ myReview ? '保存修改' : '提交评价' }}
              </el-button>
            </div>
          </div>

          <!-- My existing review -->
          <div v-if="myReview && !showReviewForm" class="review-item is-mine">
            <div class="review-header">
              <div class="review-user">
                <span class="review-username">{{ myReview.username || '我' }}</span>
                <el-rate v-model="myReview.rating" disabled :max="5" size="small" />
              </div>
              <span class="review-date">{{ formatReviewDate(myReview.created_at) }}</span>
            </div>
            <p v-if="myReview.content" class="review-content">{{ myReview.content }}</p>
            <div class="review-actions">
              <el-button link type="primary" size="small" @click="editMyReview">编辑</el-button>
              <el-button link type="danger" size="small" @click="deleteMyReview">删除</el-button>
            </div>
          </div>

          <!-- Review List -->
          <div v-if="reviews.length > 0" class="review-list">
            <div v-for="item in reviews" :key="item.id" class="review-item">
              <div class="review-header">
                <div class="review-user">
                  <span class="review-avatar">{{ (item.username || '?')[0] }}</span>
                  <span class="review-username">{{ item.username || '匿名' }}</span>
                  <el-rate v-model="item.rating" disabled :max="5" size="small" />
                </div>
                <span class="review-date">{{ formatReviewDate(item.created_at) }}</span>
              </div>
              <p v-if="item.content" class="review-content">{{ item.content }}</p>
            </div>
          </div>
          <div v-else class="review-empty">
            <span class="material-symbols-outlined">rate_review</span>
            <p>暂无评价，成为第一个评价的人吧</p>
          </div>

          <!-- Review Pagination -->
          <div v-if="reviewTotal > reviewPageSize" class="review-pagination">
            <el-pagination
              v-model:current-page="reviewPage"
              v-model:page-size="reviewPageSize"
              :total="reviewTotal"
              layout="prev, pager, next"
              small
              @current-change="loadReviews"
            />
          </div>
        </section>

        <!-- AI Quiz -->
        <section class="detail-section">
          <h2 class="section-title">
            <span class="material-symbols-outlined ai-icon">auto_awesome</span>
            智能出题
          </h2>
          <div class="ai-glass quiz-area">
            <div class="quiz-controls" v-if="chapters.length > 0">
              <label class="quiz-label">选择章节：</label>
              <select v-model="selectedChapterTitle" class="quiz-select" @change="questions = []">
                <option v-for="ch in chapters" :key="ch.id" :value="ch.title">{{ ch.title }}</option>
              </select>
            </div>
            <div class="quiz-empty" v-if="!questions.length">
              <span class="material-symbols-outlined">quiz</span>
              <p>基于课程内容智能生成练习题，巩固学习效果</p>
              <button class="btn-ai" :disabled="quizLoading" @click="loadQuiz">
                <span class="material-symbols-outlined">{{ quizLoading ? 'hourglass_top' : 'auto_awesome' }}</span>
                {{ quizLoading ? '正在生成题目...' : '生成题目' }}
              </button>
            </div>
            <div v-else class="quiz-list">
              <div v-for="(q, index) in questions" :key="index" class="quiz-item">
                <p class="quiz-q"><b>{{ index + 1 }}.</b> {{ q.question }}</p>
                <div v-for="opt in q.options" :key="opt" class="quiz-opt">{{ opt }}</div>
                <div class="quiz-ans-area">
                  <button v-if="!showAnswers[index]" class="quiz-show-ans" @click="toggleAnswer(index)">
                    <span class="material-symbols-outlined">visibility</span> 查看答案
                  </button>
                  <div v-else class="quiz-ans">
                    <span class="material-symbols-outlined">check_circle</span> 答案：{{ q.answer }}
                    <button class="quiz-hide-ans" @click="toggleAnswer(index)">
                      <span class="material-symbols-outlined">visibility_off</span> 隐藏
                    </button>
                  </div>
                </div>
              </div>
              <button class="btn-ai" :disabled="quizLoading" @click="loadQuiz" style="margin-top:12px">
                <span class="material-symbols-outlined">{{ quizLoading ? 'hourglass_top' : 'refresh' }}</span>
                {{ quizLoading ? '正在重新生成...' : '重新生成' }}
              </button>
            </div>
          </div>
        </section>
      </div>

      <!-- Sticky purchase sidebar -->
      <aside class="purchase-side">
        <div class="purchase-card">
          <div class="pc-cover">
            <video v-if="course.video_url && course.is_purchased" :src="course.video_url" controls class="pc-video" preload="metadata">
              您的浏览器不支持视频播放
            </video>
            <el-image v-else :src="course.cover || ''" fit="cover">
              <template #error>
                <div class="cover-fallback">
                  <span class="material-symbols-outlined">menu_book</span>
                </div>
              </template>
            </el-image>
          </div>

          <div class="pc-price">
            <template v-if="course.is_purchased">
              <span class="pc-owned-badge">已购买</span>
            </template>
            <template v-else-if="course.seckill_price && !seckillExpired">
              <span class="pc-seckill-price is-seckill">¥{{ course.seckill_price }}</span>
              <span class="pc-original">¥{{ seckillOriginalPrice }}</span>
            </template>
            <template v-else>
              <span class="pc-seckill-price">¥{{ skus.find(s => s.id === selectedSkuId)?.price || '?' }}</span>
            </template>
          </div>

          <div class="pc-actions">
            <template v-if="course.is_purchased">
              <RouterLink :to="`/learn/${course.id}`" class="pc-btn pc-btn-primary" style="text-decoration:none;display:flex;align-items:center;justify-content:center;">
                <span class="material-symbols-outlined" style="font-size:18px">play_circle</span> 立即观看
              </RouterLink>
            </template>
            <template v-else>
              <button v-if="course.seckill_activity_id && !seckillExpired" class="pc-btn pc-btn-seckill" :disabled="seckillPolling" @click="startSeckill">
                <span class="material-symbols-outlined">bolt</span> 秒杀抢购
              </button>
              <button class="pc-btn pc-btn-primary" @click="buyNow">
                <span class="material-symbols-outlined">{{ selectedSkuPaid ? 'shopping_cart' : 'library_add' }}</span>
                {{ selectedSkuPaid ? '立即购买' : '加入课程' }}
              </button>
              <button v-if="selectedSkuPaid" class="pc-btn pc-btn-ghost" @click="addToCart">
                <span class="material-symbols-outlined">add_shopping_cart</span> 加入购物车
              </button>
            </template>
          </div>
          <div class="pc-fav-row">
            <FavoriteButton
              v-if="course"
              :course-id="course.id"
              variant="inline"
              class="pc-fav-btn"
            />
            <span class="pc-fav-text">收藏课程</span>
          </div>

          <div class="pc-features">
            <div v-if="selectedSkuPaid" class="pcf-item">
              <span class="material-symbols-outlined">check_circle</span> 永久有效
            </div>
            <div v-else-if="allSkusFree" class="pcf-item">
              <span class="material-symbols-outlined">check_circle</span> 永久免费
            </div>
            <div v-else class="pcf-item">
              <span class="material-symbols-outlined">preview</span> 试看3课时
            </div>
            <div class="pcf-item">
              <span class="material-symbols-outlined">devices</span> 多端学习
            </div>
            <div class="pcf-item">
              <span class="material-symbols-outlined">support</span> 专属答疑
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { generateQuiz, type QuizQuestion } from '@/api/ai'
import { getCourse, getCourseChapters, getCourseSkus, type ChapterData, type Course, type CourseSku } from '@/api/courses'
import { createOrder } from '@/api/orders'
import { getSeckillResult, submitSeckill } from '@/api/seckill'
import { useCartStore } from '@/stores/cart'
import { useUserStore } from '@/stores/user'
import { createCourseReview, deleteCourseReview, listCourseReviews, updateCourseReview, type Review } from '@/api/reviews'
import FavoriteButton from '@/components/FavoriteButton.vue'

const userStore = useUserStore()

const route = useRoute()
const router = useRouter()
const cartStore = useCartStore()
const course = ref<Course>()
const skus = ref<CourseSku[]>([])
const selectedSkuId = ref<number>()
const questions = ref<QuizQuestion[]>([])
const quizLoading = ref(false)
const showAnswers = ref<Record<number, boolean>>({})

function toggleAnswer(index: number) {
  showAnswers.value[index] = !showAnswers.value[index]
}
const chapters = ref<ChapterData[]>([])
const selectedChapterTitle = ref('')

const seckillOriginalPrice = computed(() => {
  const paid = skus.value.filter((s) => Number(s.price) > 0)
  const pool = paid.length ? paid : skus.value
  if (!pool.length) return '?'
  const max = pool.reduce((m, s) => (Number(s.price) > Number(m) ? Number(s.price) : Number(m)), 0)
  return max > 0 ? `¥${max.toFixed(2)}` : '?'
})
const selectedSkuPaid = computed(() => {
  const sku = skus.value.find((s) => s.id === selectedSkuId.value)
  return sku ? Number(sku.price) > 0 : false
})
const allSkusFree = computed(() => skus.value.length > 0 && skus.value.every(s => Number(s.price) === 0))
const seckillExpired = computed(() => {
  if (!course.value?.seckill_end_time) return true
  return new Date(course.value.seckill_end_time).getTime() <= Date.now()
})
const loading = ref(false)
const loadError = ref('')
const seckillPolling = ref(false)

/* ===== Reviews ===== */
const reviews = ref<Review[]>([])
const reviewTotal = ref(0)
const reviewAvg = ref(0)
const reviewCount = ref(0)
const reviewPage = ref(1)
const reviewPageSize = ref(10)
const myReview = ref<Review | null>(null)
const showReviewForm = ref(false)
const reviewSubmitting = ref(false)
const reviewForm = ref({ rating: 5, content: '' })

function formatReviewDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch { return dateStr }
}

async function loadReviews() {
  if (!course.value) return
  try {
    const res = await listCourseReviews(course.value.id, { page: reviewPage.value, page_size: reviewPageSize.value })
    reviews.value = res.items
    reviewTotal.value = res.total
    reviewAvg.value = res.average_rating
    reviewCount.value = res.review_count

    // Check if current user has a review
    if (userStore.isLoggedIn && userStore.user) {
      myReview.value = res.items.find((r) => r.user_id === userStore.user!.id) || null
    }
  } catch {
    reviews.value = []
  }
}

function openReviewForm() {
  reviewForm.value = { rating: 5, content: '' }
  showReviewForm.value = true
}

function cancelReviewForm() {
  showReviewForm.value = false
  if (myReview.value) {
    reviewForm.value = { rating: myReview.value.rating, content: myReview.value.content || '' }
  }
}

function editMyReview() {
  if (!myReview.value) return
  reviewForm.value = { rating: myReview.value.rating, content: myReview.value.content || '' }
  showReviewForm.value = true
}

async function submitReview() {
  if (!course.value) return
  reviewSubmitting.value = true
  try {
    if (myReview.value) {
      const updated = await updateCourseReview(course.value.id, myReview.value.id, reviewForm.value)
      ElMessage.success('评价已更新')
      // Update local state
      Object.assign(myReview.value, updated)
    } else {
      await createCourseReview(course.value.id, reviewForm.value)
      ElMessage.success('评价已提交')
    }
    showReviewForm.value = false
    await loadReviews()
  } catch {
    // handled by interceptor
  } finally {
    reviewSubmitting.value = false
  }
}

async function deleteMyReview() {
  if (!course.value || !myReview.value) return
  try {
    await ElMessageBox.confirm('确定删除你的评价？', '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await deleteCourseReview(course.value.id, myReview.value.id)
    ElMessage.success('评价已删除')
    myReview.value = null
    showReviewForm.value = false
    await loadReviews()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function addToCart() {
  if (!selectedSkuId.value) return ElMessage.warning('请选择版本')
  try {
    await cartStore.add(selectedSkuId.value)
    ElMessage.success('已加入购物车')
  } catch {
    // error handled by interceptor
  }
}

async function buyNow() {
  if (!selectedSkuId.value) return ElMessage.warning('请选择版本')
  try {
    const order = await createOrder([selectedSkuId.value])
    if (order.direct_granted) {
      ElMessage.success('免费课程已加入我的学习')
      router.push('/my-courses')
    } else {
      router.push(`/pay/${order.order_sn}`)
    }
  } catch {
    // error handled by interceptor
  }
}

async function startSeckill() {
  if (!course.value?.seckill_activity_id || !selectedSkuId.value) return
  if (seckillPolling.value) return
  if (seckillExpired.value) {
    ElMessage.warning('秒杀活动已结束')
    return
  }
  seckillPolling.value = true
  const startTime = Date.now()
  let toast = ElMessage.info('正在排队...')
  try {
    const queue = await submitSeckill(course.value.seckill_activity_id)
    let delay = 1000
    const maxDelay = 10000
    const maxDuration = 60000
    while (seckillPolling.value) {
      const elapsed = Math.floor((Date.now() - startTime) / 1000)
      if (elapsed > maxDuration / 1000) {
        ElMessage.info('排队人数较多，请稍后在订单中查看')
        return
      }
      await new Promise((resolve) => window.setTimeout(resolve, delay))
      if (!seckillPolling.value) return
      const result = await getSeckillResult(queue.queue_id)
      if (result.status === 'success' && result.order_sn) {
        toast.close()
        ElMessage.success(result.message || '秒杀成功')
        router.push(`/pay/${result.order_sn}`)
        return
      }
      if (result.status === 'failed') {
        toast.close()
        ElMessage.error(result.message || '秒杀失败')
        return
      }
      // Still queued — update message and increase delay
      toast.close()
      toast = ElMessage.info(`正在排队... ${elapsed}s`)
      delay = Math.min(delay * 1.5, maxDelay)
    }
  } catch {
    toast.close()
    // error already shown by axios interceptor
  } finally {
    seckillPolling.value = false
  }
}

async function loadQuiz() {
  if (!course.value) return
  quizLoading.value = true
  const chapterTitle = selectedChapterTitle.value || chapters.value[0]?.title || '第一章'
  const chapter = chapters.value.find(c => c.title === chapterTitle)
  const points = chapter
    ? chapter.lessons.map(l => l.title).filter(Boolean)
    : []
  // Ensure at least course title & desc as context so LLM doesn't guess generic content
  const payloadCourseTitle = course.value.title
  const payloadCourseDesc = (course.value.description || '').slice(0, 200)
  if (points.length === 0) {
    points.push(payloadCourseTitle)
    if (payloadCourseDesc) points.push(payloadCourseDesc)
  }
  try {
    const result = await generateQuiz({
      course_id: course.value.id,
      chapter_title: chapterTitle,
      knowledge_points: points.length > 0 ? points : [payloadCourseTitle],
    })
    questions.value = result.questions
    showAnswers.value = {}
  } catch {
    ElMessage.error('生成题目失败，请稍后再试')
  } finally {
    quizLoading.value = false
  }
}

onMounted(async () => {
  const id = Number(route.params.id)
  if (!id || Number.isNaN(id)) {
    loadError.value = '课程 ID 无效'
    return
  }
  loading.value = true
  try {
    course.value = await getCourse(id)
    skus.value = await getCourseSkus(id)
    const paid = skus.value.filter((s) => Number(s.price) > 0)
    selectedSkuId.value = (paid[0] || skus.value[0])?.id
    // Load chapters for quiz
    try {
      chapters.value = await getCourseChapters(id)
      if (chapters.value.length > 0) {
        selectedChapterTitle.value = chapters.value[0].title
      }
    } catch {
      // chapters unavailable
    }
  } catch {
    loadError.value = '课程加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
  await loadReviews()
})

onUnmounted(() => {
  seckillPolling.value = false
})
</script>

<style scoped>
.cd-loading, .cd-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  gap: 12px;
  color: var(--on-surface-variant);
}
.cd-loading .material-symbols-outlined { font-size: 56px; color: var(--primary); }
.cd-error .material-symbols-outlined { font-size: 64px; opacity: 0.4; }
.cd-spin { animation: cd-spin 1s linear infinite; }
@keyframes cd-spin { to { transform: rotate(360deg); } }

.detail-layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 28px;
  align-items: start;
}

/* Main content */
.main-content { min-width: 0; }

.course-header { margin-bottom: 28px; }
.ch-inline { display: flex; gap: 8px; margin-bottom: 16px; }
.ch-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 12px;
  letter-spacing: -0.01em;
}
.ch-desc { font-size: 16px; line-height: 1.6; margin: 0 0 16px; }
.ch-meta {
  display: flex; flex-wrap: wrap; gap: 16px;
  font-size: 14px; color: var(--on-surface-variant);
  align-items: center;
}
.ch-category {
  background: var(--surface-container-low);
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
}
.ch-rate {
  display: inline-flex; align-items: center; gap: 2px;
  color: var(--warning);
  font-weight: 600;
}
.ch-rate .material-symbols-outlined { font-size: 16px; }

.section-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ai-icon { color: var(--secondary); font-size: 24px; }
.section-subtitle {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 14px;
}

.sku-section { margin-bottom: 28px; }
.sku-options { display: flex; flex-direction: column; gap: 10px; }
.sku-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px 18px;
  border-radius: var(--radius);
  border: 2px solid var(--outline-variant);
  background: var(--surface-container-lowest);
  cursor: pointer;
  transition: all 0.2s;
}
.sku-card:hover { border-color: var(--primary); }
.sku-active {
  border-color: var(--primary);
  background: var(--primary-fixed);
}
.sku-main { display: flex; justify-content: space-between; align-items: center; }
.sku-name { font-weight: 600; font-size: 15px; color: var(--on-surface); }
.sku-price { font-weight: 700; font-size: 18px; color: var(--primary); }
.sku-sub {
  display: flex; gap: 16px;
  font-size: 13px;
  color: var(--on-surface-variant);
}

.detail-section { margin-bottom: 28px; }
.desc-text { line-height: 1.7; }

/* ===== Reviews ===== */
.review-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  background: var(--surface-container-low);
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
}
.review-summary-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.review-avg-num {
  font-size: 40px;
  font-weight: 800;
  color: var(--on-surface);
  line-height: 1;
}
.review-count-text {
  font-size: 13px;
  color: var(--on-surface-variant);
}
.review-write-trigger {
  margin-bottom: 16px;
}
.review-write-box {
  background: var(--surface-container-low);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.review-write-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
.review-write-label {
  font-weight: 600;
  font-size: 15px;
}
.review-write-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.review-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.review-item {
  padding: 16px;
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius);
  transition: background 0.15s;
}
.review-item:hover { background: var(--surface-container-low); }
.review-item.is-mine {
  border-color: var(--primary);
  background: var(--primary-fixed);
}
.review-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.review-user {
  display: flex;
  align-items: center;
  gap: 8px;
}
.review-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}
.review-username {
  font-weight: 600;
  font-size: 14px;
}
.review-date {
  font-size: 12px;
  color: var(--on-surface-variant);
}
.review-content {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--on-surface);
}
.review-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.review-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--on-surface-variant);
}
.review-empty .material-symbols-outlined { font-size: 48px; opacity: 0.4; }
.review-empty p { margin: 8px 0 0; font-size: 14px; }
.review-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.quiz-area { padding: 24px; }
.quiz-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.quiz-label { font-size: 13px; color: var(--on-surface-variant); white-space: nowrap; }
.quiz-select {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  font-size: 13px;
  color: var(--on-surface);
  outline: none;
  cursor: pointer;
  transition: border 0.2s;
}
.quiz-select:focus { border-color: var(--primary); }
.quiz-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--on-surface-variant);
}
.quiz-empty .material-symbols-outlined { font-size: 48px; opacity: 0.5; }
.quiz-empty p { margin: 10px 0 18px; font-size: 14px; }
.quiz-list { display: flex; flex-direction: column; gap: 16px; }
.quiz-item { background: var(--surface-container-lowest); border-radius: var(--radius); padding: 16px; border: 1px solid var(--outline-variant); }
.quiz-q { margin: 0 0 10px; font-size: 15px; line-height: 1.5; }
.quiz-opt { padding: 4px 12px; font-size: 14px; color: var(--on-surface-variant); }
.quiz-ans {
  margin-top: 10px;
  display: flex; align-items: center; gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--tertiary);
}
.quiz-ans .material-symbols-outlined { font-size: 18px; }
.quiz-ans-area { margin-top: 10px; }
.quiz-show-ans,
.quiz-hide-ans {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  color: var(--primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.quiz-show-ans:hover,
.quiz-hide-ans:hover {
  background: var(--primary-container);
  border-color: var(--primary);
}
.quiz-hide-ans {
  margin-left: 12px;
  color: var(--on-surface-variant);
  font-weight: 400;
}

/* Purchase sidebar */
.purchase-side { position: sticky; top: 88px; }
.purchase-card {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev-1);
  overflow: hidden;
}

.pc-cover { height: 180px; }
.pc-cover .el-image { width: 100%; height: 100%; }
.pc-video { width: 100%; height: 100%; object-fit: cover; background: #000; }

.pc-price { padding: 20px 20px 0; display: flex; align-items: baseline; gap: 10px; }
.pc-seckill-price { font-size: 28px; font-weight: 800; color: var(--primary); }
.pc-seckill-price.is-seckill { color: var(--danger); }
.pc-original { font-size: 16px; color: var(--outline); text-decoration: line-through; }
.pc-owned-badge { font-size: 16px; font-weight: 600; color: var(--tertiary); padding: 4px 12px; border-radius: var(--radius-full); background: var(--tertiary-container); }

.pc-actions { padding: 16px 20px 0; display: flex; flex-direction: column; gap: 10px; }
.pc-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%;
  padding: 14px;
  border-radius: var(--radius);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s;
  font-family: inherit;
  border: none;
}
.pc-btn-primary { background: var(--primary); color: var(--on-primary); }
.pc-btn-primary:hover { opacity: 0.9; }
.pc-btn-seckill {
  background: var(--danger);
  color: #fff;
  box-shadow: 0 4px 14px rgba(255, 86, 48, 0.35);
}
.pc-btn-seckill:hover { opacity: 0.9; }
.pc-btn-ghost {
  background: var(--surface-container-low);
  color: var(--on-surface);
  border: 1px solid var(--outline-variant);
  font-weight: 600;
}
.pc-btn-ghost:hover { background: var(--surface-container); }

.pc-fav-row {
  padding: 12px 20px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.pc-fav-text {
  font-size: 14px;
  color: var(--on-surface-variant);
  font-weight: 500;
}

.pc-features {
  padding: 16px 20px 20px;
  display: flex; flex-direction: column; gap: 10px;
}
.pcf-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.pcf-item .material-symbols-outlined { font-size: 18px; color: var(--tertiary); }

@media (max-width: 960px) {
  .detail-layout { grid-template-columns: 1fr; }
  .purchase-side { position: static; }
  .purchase-card { display: grid; grid-template-columns: 1fr 1fr; }
  .pc-cover { height: 100%; }
  .pc-features { flex-direction: row; flex-wrap: wrap; }
}
@media (max-width: 560px) {
  .ch-title { font-size: 26px; }
  .purchase-card { grid-template-columns: 1fr; }
  .pc-cover { height: 160px; }
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
  font-size: 64px;
  opacity: 0.5;
  color: var(--on-primary-container);
}
</style>