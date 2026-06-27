<template>
  <div class="container">
    <!-- 页头：AI 大搜索栏 -->
    <div class="search-hero">
      <h1 class="page-title">探索 <span class="ai-gradient-text">AI 学习宇宙</span></h1>
      <p class="muted page-sub">让 AI 为你推荐最合适的课程，按兴趣、目标和当前水平精准匹配</p>
      <div class="big-search">
        <span class="material-symbols-outlined search-i">search</span>
        <input
          v-model="keyword"
          class="big-search-input"
          placeholder="试试搜索：大模型应用、机器学习、Python 数据分析..."
          @keyup.enter="load(1)"
        />
        <button class="big-search-btn" @click="load(1)">
          <span class="material-symbols-outlined">auto_awesome</span>
          AI 搜索
        </button>
      </div>
      <div class="hot-tags">
        <span class="hot-label">热门搜索</span>
        <button v-for="tag in hotTags" :key="tag" class="hot-tag" @click="keyword = tag; load(1)">
          {{ tag }}
        </button>
      </div>
    </div>

    <!-- 主体：左侧筛选 + 右侧列表 -->
    <div class="layout">
      <aside class="filters-side">
        <div class="filter-panel">
          <h3 class="filter-title">
            <span class="material-symbols-outlined">tune</span> 筛选条件
          </h3>

          <div class="filter-group">
            <p class="filter-label">分类</p>
            <div class="filter-options">
              <button
                v-for="cat in categories"
                :key="cat.value"
                class="filter-chip"
                :class="{ active: category === cat.value }"
                @click="category = category === cat.value ? '' : cat.value; load(1)"
              >
                {{ cat.label }}
              </button>
            </div>
          </div>

          <div class="filter-group">
            <p class="filter-label">价格排序</p>
            <div class="filter-options">
              <button
                class="filter-chip"
                :class="{ active: priceSort === 'asc' }"
                @click="priceSort = priceSort === 'asc' ? '' : 'asc'; load(1)"
              >从低到高</button>
              <button
                class="filter-chip"
                :class="{ active: priceSort === 'desc' }"
                @click="priceSort = priceSort === 'desc' ? '' : 'desc'; load(1)"
              >从高到低</button>
            </div>
          </div>

          <button class="reset-btn" @click="reset">
            <span class="material-symbols-outlined">refresh</span> 重置筛选
          </button>
        </div>

        <div class="ai-tip ai-glass">
          <span class="material-symbols-outlined">auto_awesome</span>
          <p>共发现 <b>{{ total }}</b> 门匹配课程</p>
        </div>
      </aside>

      <main class="result-side">
        <div v-if="!courses.length && !loading" class="empty-state">
          <span class="material-symbols-outlined">search_off</span>
          <p>暂无匹配课程</p>
        </div>
        <div v-else class="result-grid">
          <CourseCard v-for="course in courses" :key="course.id" :course="course" />
        </div>
        <div class="pagination-wrap">
          <PaginationBar :total="total" :page="page" :page-size="pageSize" @change="load" />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { listCourses, searchCourses, type Course } from '@/api/courses'
import CourseCard from '@/components/CourseCard.vue'
import PaginationBar from '@/components/PaginationBar.vue'

const route = useRoute()
const courses = ref<Course[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const keyword = ref('')
const category = ref('')
const priceSort = ref('')
const loading = ref(false)

const categories = [
  { label: 'AI', value: 'AI' },
  { label: 'Python', value: 'Python' },
  { label: '前端', value: '前端' },
  { label: '机器学习', value: '机器学习' },
  { label: '数据分析', value: '数据分析' },
]

const hotTags = ['大模型', '深度学习', 'Pandas', '提示词工程', 'Vue3']

async function load(nextPage = page.value) {
  page.value = nextPage
  loading.value = true
  try {
    if (keyword.value) {
      // Use ES-powered search for keyword queries
      const result = await searchCourses({
        keyword: keyword.value,
        category: category.value || undefined,
        sort: priceSort.value === 'asc' ? 'price_asc' : priceSort.value === 'desc' ? 'price_desc' : undefined,
        page: page.value,
        size: pageSize,
      })
      courses.value = result.items.map((item: { course_id: number; title: string; cover?: string | null; price: number; teacher_name: string; sales: number; highlight?: string[] }) => ({
        id: item.course_id,
        title: item.title,
        cover: item.cover,
        learn_count: item.sales,
        rating: 0,
        total_hours: 0,
        teacher_id: 0,
        status: 'published',
        teacher: { id: 0, name: item.teacher_name, avatar: null },
        skus: [{ id: 0, course_id: item.course_id, sku_name: null, price: String(item.price), stock: 0, validity_days: 365, status: 'on' }] as Course['skus'],
      })) as unknown as Course[]
      total.value = result.total
    } else {
      const result = await listCourses({
        page: page.value,
        page_size: pageSize,
        keyword: keyword.value || undefined,
        category: category.value || undefined,
        price_sort: priceSort.value || undefined,
      })
      courses.value = result.items
      total.value = result.total
    }
  } catch {
    courses.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function reset() {
  keyword.value = ''
  category.value = ''
  priceSort.value = ''
  load(1)
}

watch(() => route.query.keyword, (k) => {
  if (typeof k === 'string') { keyword.value = k; load(1) }
}, { immediate: false })

onMounted(() => {
  if (typeof route.query.keyword === 'string') keyword.value = route.query.keyword
  load()
})
</script>

<style scoped>
.search-hero { text-align: center; padding: 40px 0 32px; }
.page-title { font-size: 40px; margin-bottom: 8px; letter-spacing: -0.02em; }
.page-sub { font-size: 16px; margin: 0 0 28px; }

.big-search {
  display: flex; align-items: center;
  max-width: 720px;
  margin: 0 auto;
  height: 60px;
  padding: 0 6px 0 22px;
  border-radius: 30px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  box-shadow: var(--elev-1);
  transition: all 0.25s;
}
.big-search:focus-within {
  border-color: var(--secondary);
  box-shadow: 0 0 0 5px rgba(101, 84, 192, 0.12), var(--elev-2);
}
.search-i { font-size: 24px; color: var(--outline); }
.big-search-input {
  flex: 1;
  height: 100%;
  padding: 0 16px;
  font-size: 15px;
  background: transparent;
  border: none;
  outline: none;
  font-family: inherit;
  color: var(--on-surface);
}
.big-search-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 48px;
  padding: 0 24px;
  border-radius: 24px;
  background: var(--ai-gradient);
  color: #fff;
  border: none;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(101, 84, 192, 0.32);
  transition: transform 0.2s;
}
.big-search-btn:hover { transform: scale(1.03); }
.big-search-btn .material-symbols-outlined { font-size: 18px; }

.hot-tags { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 18px; }
.hot-label { font-size: 13px; color: var(--on-surface-variant); align-self: center; }
.hot-tag {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  font-size: 13px;
  color: var(--on-surface-variant);
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.hot-tag:hover { background: var(--ai-gradient-soft); color: var(--secondary); border-color: var(--secondary); }

.layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 32px;
  margin-top: 8px;
}

.filters-side {
  display: flex; flex-direction: column; gap: 16px;
  position: sticky;
  top: 88px;
  align-self: start;
  max-height: calc(100vh - 96px);
  overflow-y: auto;
}
.filter-panel {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--elev-1);
}
.filter-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 16px; font-weight: 700;
  margin: 0 0 20px;
  color: var(--on-surface);
}
.filter-title .material-symbols-outlined { font-size: 20px; color: var(--primary); }
.filter-group { margin-bottom: 20px; }
.filter-label {
  font-size: 12px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--on-surface-variant);
  margin: 0 0 10px;
}
.filter-options { display: flex; flex-wrap: wrap; gap: 8px; }
.filter-chip {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  border: 1px solid var(--outline-variant);
  background: transparent;
  font-size: 13px;
  color: var(--on-surface-variant);
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}
.filter-chip:hover { border-color: var(--primary); color: var(--primary); }
.filter-chip.active {
  background: var(--primary);
  color: var(--on-primary);
  border-color: var(--primary);
}
.reset-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  width: 100%;
  padding: 10px;
  border-radius: var(--radius);
  background: var(--surface-container-low);
  border: 1px solid var(--outline-variant);
  color: var(--on-surface-variant);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}
.reset-btn:hover { background: var(--surface-container); }
.reset-btn .material-symbols-outlined { font-size: 16px; }

.ai-tip {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px;
  font-size: 13px;
  color: var(--on-surface);
}
.ai-tip .material-symbols-outlined { font-size: 20px; color: var(--secondary); }
.ai-tip p { margin: 0; }
.ai-tip b { color: var(--primary); font-weight: 700; }

.result-side { min-width: 0; }
.result-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: var(--on-surface-variant);
}
.empty-state .material-symbols-outlined { font-size: 64px; opacity: 0.4; }
.empty-state p { font-size: 15px; margin: 12px 0 0; }

.pagination-wrap { margin-top: 32px; display: flex; justify-content: center; }

@media (max-width: 1100px) {
  .layout { grid-template-columns: 220px 1fr; gap: 24px; }
  .result-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 860px) {
  .layout { grid-template-columns: 1fr; }
  .filters-side { position: static; max-height: none; overflow: visible; }
  .result-grid { grid-template-columns: repeat(2, 1fr); }
  .page-title { font-size: 28px; }
}
@media (max-width: 560px) {
  .result-grid { grid-template-columns: 1fr; }
  .big-search { height: 52px; padding: 0 4px 0 16px; }
  .big-search-btn { height: 42px; padding: 0 16px; }
}
</style>