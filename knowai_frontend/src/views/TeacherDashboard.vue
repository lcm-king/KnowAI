<template>
  <div class="teacher-dashboard">
    <!-- Header with gradient -->
    <div class="teacher-header">
      <div class="teacher-header-bg"></div>
      <div class="teacher-header-content">
        <div class="teacher-header-left">
          <span class="teacher-icon">
            <span class="material-symbols-outlined">menu_book</span>
          </span>
          <div>
            <h1 class="teacher-title">讲师工作台</h1>
            <p class="teacher-subtitle">教学管理与营收中心</p>
          </div>
        </div>
        <div class="teacher-header-right">
          <el-tag effect="dark" round type="warning">
            <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle">workspace</span> 讲师身份
          </el-tag>
        </div>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="teacher-stats">
      <div class="stat-card stat-orange">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">menu_book</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ totalCourses }}</p>
          <p class="stat-label">课程总数</p>
        </div>
      </div>
      <div class="stat-card stat-gold">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">payments</span></div>
        <div class="stat-info">
          <p class="stat-value">¥{{ formatAmount(sales.total_sales) }}</p>
          <p class="stat-label">本月营收</p>
        </div>
      </div>
      <div class="stat-card stat-teal">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">shopping_bag</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ sales.order_count }}</p>
          <p class="stat-label">累计订单</p>
        </div>
      </div>
      <div class="stat-card stat-emerald">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">trending_up</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ sales.hot_courses.length }}</p>
          <p class="stat-label">热门课程</p>
        </div>
      </div>
    </div>

    <!-- Tab Panel -->
    <div class="teacher-panel">
      <el-tabs v-model="tab" class="teacher-tabs">
        <el-tab-pane label="📋 课程管理" name="courses">
          <div class="tab-toolbar">
            <el-button type="primary" size="large" @click="openCreate">
              <span class="material-symbols-outlined">add</span> 新增课程
            </el-button>
          </div>
          <el-table :data="courses" class="styled-table" v-loading="loadingCourses" stripe>
            <el-table-column prop="title" label="课程名称" min-width="200" />
            <el-table-column prop="category" label="分类" width="120" />
            <el-table-column label="价格" width="100">
              <template #default="{ row }">
                <span v-if="row.price !== null && row.price !== undefined && Number(row.price) > 0">¥{{ Number(row.price).toFixed(2) }}</span>
                <span v-else style="color:var(--on-surface-variant)">免费</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" effect="light" round size="small">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="220">
              <template #default="{ row }">
                <el-button v-if="row.status === 'draft'" link type="primary" @click="handleSubmit(row)">
                  <span class="material-symbols-outlined" style="font-size:16px">send</span> 提交审核
                </el-button>
                <el-button link type="warning" @click="openEdit(row)">
                  <span class="material-symbols-outlined" style="font-size:16px">edit</span> 编辑
                </el-button>
                <el-button v-if="row.status === 'published'" link type="danger" @click="handleClose(row)">
                  <span class="material-symbols-outlined" style="font-size:16px">close_fullscreen</span> 下架
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="📊 销售看板" name="sales">
          <div v-if="!sales.hot_courses.length && !loadingSales" class="empty-mini">暂无销售数据</div>
          <div ref="chartRef" class="chart" v-loading="loadingSales" />
          <div v-if="sales.hot_courses.length" class="hot-list">
            <h3 class="hot-title">
              <span class="material-symbols-outlined">emoji_events</span> 热门课程 TOP{{ sales.hot_courses.length }}
            </h3>
            <div v-for="(item, idx) in sales.hot_courses" :key="item.id" class="hot-row">
              <div class="hot-left">
                <span class="hot-rank" :class="'rank-' + (idx + 1)">{{ idx + 1 }}</span>
                <span class="hot-name">{{ item.title }}</span>
              </div>
              <span class="hot-sold">
                <span class="material-symbols-outlined" style="font-size:16px">shopping_cart</span> 已售 {{ item.sold }}
              </span>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="⚡ 秒杀活动" name="seckill">
          <div class="tab-toolbar">
            <el-button type="danger" size="large" @click="openSeckillDialog">
              <span class="material-symbols-outlined">add</span> 申请秒杀
            </el-button>
          </div>
          <el-table :data="seckills" class="styled-table" v-loading="loadingSeckills" stripe>
            <el-table-column prop="course_title" label="课程" min-width="160" />
            <el-table-column label="秒杀价" width="100">
              <template #default="{ row }">¥{{ row.seckill_price }}</template>
            </el-table-column>
            <el-table-column prop="stock" label="库存" width="80" />
            <el-table-column label="时间范围" min-width="220">
              <template #default="{ row }">{{ formatSeckillDate(row.start_time) }} ~ {{ formatSeckillDate(row.end_time) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="seckillStatusType(row.status)" effect="light" round size="small">
                  {{ seckillStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="📖 内容管理" name="content">
          <div class="tab-toolbar">
            <el-select v-model="contentCourseId" placeholder="选择课程" size="large" style="width:300px" @change="loadContent">
              <el-option
                v-for="c in courses"
                :key="c.id"
                :label="c.title"
                :value="c.id"
              />
            </el-select>
            <el-button type="primary" size="large" :disabled="!contentCourseId" @click="openChapterDialog">新增章节</el-button>
          </div>
          <div v-if="contentCourseId && !loadingContent" class="content-area">
            <div v-if="!chapters.length" class="empty-mini">暂无章节，请点击「新增章节」开始创建</div>
            <div v-for="chapter in chapters" :key="chapter.id" class="content-chapter">
              <div class="content-chapter-header">
                <span class="content-chapter-title">{{ chapter.title }}</span>
                <div class="content-chapter-actions">
                  <el-button link type="primary" size="small" @click="openLessonDialog(chapter.id)">添加课时</el-button>
                  <el-button link type="warning" size="small" @click="editChapter(chapter)">编辑</el-button>
                  <el-button link type="danger" size="small" @click="handleDeleteChapter(chapter)">删除</el-button>
                </div>
              </div>
              <div class="content-lessons">
                <div v-for="lesson in chapter.lessons" :key="lesson.id" class="content-lesson-item">
                  <span class="content-lesson-title">{{ lesson.title }}</span>
                  <span class="content-lesson-duration">{{ formatDuration(lesson.duration) }}</span>
                  <div class="content-lesson-actions">
                    <el-button link type="warning" size="small" @click="editLesson(lesson)">编辑</el-button>
                    <el-button link type="danger" size="small" @click="handleDeleteLesson(lesson)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="loadingContent" v-loading="loadingContent" class="empty-mini">加载中...</div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑课程' : '新增课程'" width="520px" class="styled-dialog">
      <el-form label-position="top">
        <el-form-item label="课程标题"><el-input v-model="form.title" size="large" placeholder="请输入课程标题" /></el-form-item>
        <el-form-item label="课程封面">
          <div class="cover-upload-wrap">
            <img v-if="form.cover" :src="form.cover" class="cover-preview" />
            <input type="file" ref="coverInputRef" accept="image/jpeg,image/png,image/gif,image/webp" style="display:none" @change="onCoverFileChange" />
            <el-button size="small" @click="triggerCoverInput">{{ form.cover ? '更换封面' : '上传封面' }}</el-button>
            <span class="cover-hint">建议尺寸 800×480，支持 JPG/PNG/GIF/WebP，最大 5MB</span>
          </div>
        </el-form-item>
        <el-form-item label="课程分类"><el-input v-model="form.category" size="large" placeholder="如：AI / Python / 前端" /></el-form-item>
        <el-form-item label="课程简介"><el-input v-model="form.description" type="textarea" :rows="3" placeholder="课程简介..." /></el-form-item>
        <el-form-item label="课程视频（预告片）">
          <div class="video-upload-wrap">
            <video v-if="form.video_url" :src="form.video_url" controls class="video-preview" />
            <input type="file" ref="courseVideoInputRef" accept="video/mp4,video/webm,video/x-msvideo" style="display:none" @change="onCourseVideoFileChange" />
            <el-button size="small" @click="triggerCourseVideoInput">{{ form.video_url ? '更换视频' : '上传视频' }}</el-button>
            <span class="cover-hint">支持 MP4/WebM/AVI，最大 200MB</span>
          </div>
        </el-form-item>
        <el-form-item label="视频地址">
          <el-input v-model="form.video_url" size="large" placeholder="上传视频或粘贴预告片 URL" />
        </el-form-item>
        <el-divider />
        <p style="margin:0 0 8px;font-size:13px;color:var(--on-surface-variant)">定价信息</p>
        <el-form-item label="价格（元）">
          <el-input-number v-model="form.price" :min="0" :precision="2" style="width:100%" placeholder="设为 0 即为免费课程" />
        </el-form-item>
        <el-divider />
        <p style="margin:0 0 8px;font-size:13px;color:var(--on-surface-variant)">知识库文档</p>
        <el-form-item label="课程知识库">
          <div class="knowledge-section">
            <div v-if="courseKnowledgeFiles.length || pendingKnowledgeFiles.length" class="knowledge-list">
              <div v-for="kf in courseKnowledgeFiles" :key="kf.id" class="knowledge-item">
                <span class="material-symbols-outlined kf-icon">description</span>
                <div class="kf-info">
                  <span class="kf-name">{{ kf.file_name }}</span>
                  <span class="kf-meta">{{ (kf.file_size / 1024).toFixed(1) }} KB</span>
                </div>
                <el-button text type="danger" size="small" @click="handleCourseKnowledgeDelete(kf)">删除</el-button>
              </div>
              <div v-for="(pf, idx) in pendingKnowledgeFiles" :key="'pending-'+idx" class="knowledge-item knowledge-pending">
                <span class="material-symbols-outlined kf-icon">schedule</span>
                <div class="kf-info">
                  <span class="kf-name">{{ pf.name }}</span>
                  <span class="kf-meta">{{ (pf.size / 1024).toFixed(1) }} KB — 待上传</span>
                </div>
                <el-button text type="danger" size="small" @click="pendingKnowledgeFiles.splice(idx, 1)">移除</el-button>
              </div>
            </div>
            <input type="file" ref="courseKnowledgeInputRef" accept=".pdf,.txt,.md,.doc,.docx" style="display:none" @change="onCourseKnowledgeFileChange" />
            <el-button size="small" :loading="courseKnowledgeUploading" @click="triggerCourseKnowledgeInput">上传文档</el-button>
            <span class="cover-hint">支持 PDF/TXT/Markdown/DOC，最大 50MB</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleSave">{{ editingId ? '保存修改' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- Seckill Request Dialog -->
    <el-dialog v-model="seckillDialogVisible" title="申请秒杀活动" width="520px" class="styled-dialog">
      <el-form label-position="top">
        <el-form-item label="选择课程 SKU">
          <el-select v-model="seckillForm.sku_id" placeholder="请先发布课程" size="large" style="width:100%">
            <el-option
              v-for="sku in teacherSkus"
              :key="sku.id"
              :label="`${sku.course_title} — ¥${sku.price}（库存 ${sku.stock}）`"
              :value="sku.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="秒杀价（元）">
          <el-input-number v-model="seckillForm.seckill_price" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="秒杀库存">
          <el-input-number v-model="seckillForm.stock" :min="1" :max="999" style="width:100%" />
        </el-form-item>
        <el-form-item label="每人限购">
          <el-input-number v-model="seckillForm.limit_quantity" :min="1" :max="10" style="width:100%" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="seckillForm.start_time" type="datetime" placeholder="选择开始时间" style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="seckillForm.end_time" type="datetime" placeholder="选择结束时间" style="width:100%" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="seckillDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="seckillCreating" @click="handleCreateSeckill">提交申请</el-button>
      </template>
    </el-dialog>

    <!-- Chapter Dialog -->
    <el-dialog v-model="chapterDialogVisible" :title="editingChapterId ? '编辑章节' : '新增章节'" width="480px" class="styled-dialog">
      <el-form label-position="top">
        <el-form-item label="章节名称">
          <el-input v-model="chapterForm.title" size="large" placeholder="请输入章节名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chapterDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="chapterSaving" @click="handleSaveChapter">{{ editingChapterId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- Lesson Dialog -->
    <el-dialog v-model="lessonDialogVisible" :title="editingLessonId ? '编辑课时' : '添加课时'" width="520px" class="styled-dialog">
      <el-form label-position="top">
        <el-form-item label="课时名称">
          <el-input v-model="lessonForm.title" size="large" placeholder="请输入课时名称" />
        </el-form-item>
        <el-form-item label="视频">
          <div class="video-upload-wrap">
            <video v-if="lessonForm.video_url" :src="lessonForm.video_url" controls class="video-preview" />
            <input type="file" ref="videoInputRef" accept="video/mp4,video/webm,video/x-msvideo" style="display:none" @change="onVideoFileChange" />
            <el-button size="small" @click="triggerVideoInput">{{ lessonForm.video_url ? '更换视频' : '上传视频' }}</el-button>
            <span class="cover-hint">支持 MP4/WebM/AVI，最大 200MB</span>
          </div>
        </el-form-item>
        <el-form-item label="视频地址">
          <el-input v-model="lessonForm.video_url" size="large" placeholder="上传视频或粘贴视频 URL" />
        </el-form-item>
        <el-form-item label="时长（秒）">
          <el-input-number v-model="lessonForm.duration" :min="0" :max="86400" style="width:100%" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="lessonForm.sort_order" :min="0" :max="999" style="width:100%" />
        </el-form-item>
        <el-form-item label="知识库文档">
          <div class="knowledge-section">
            <div v-if="knowledgeFiles.length" class="knowledge-list">
              <div v-for="kf in knowledgeFiles" :key="kf.id" class="knowledge-item">
                <span class="material-symbols-outlined kf-icon">description</span>
                <div class="kf-info">
                  <span class="kf-name">{{ kf.file_name }}</span>
                  <span class="kf-meta">{{ (kf.file_size / 1024).toFixed(1) }} KB</span>
                </div>
                <el-button text type="danger" size="small" @click="handleDeleteKnowledge(kf)">删除</el-button>
              </div>
            </div>
            <input type="file" ref="lessonKnowledgeInputRef" accept=".pdf,.txt,.md,.doc,.docx" style="display:none" @change="onLessonKnowledgeFileChange" />
            <el-button size="small" :loading="knowledgeUploading" @click="triggerLessonKnowledgeInput">上传文档</el-button>
            <span class="cover-hint">支持 PDF/TXT/Markdown/DOC，最大 50MB</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="lessonDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="lessonSaving" @click="handleSaveLesson">{{ editingLessonId ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { closeCourse, createCourse, createTeacherSeckill, getTeacherSales, listTeacherCourses, listTeacherSeckills, listTeacherSkus, submitCourse, updateCourse } from '@/api/teacher'
import { createChapter, createLesson, deleteChapter, deleteLesson, getTeacherChapters, updateChapter, updateLesson } from '@/api/teacher'
import { getLessonKnowledge, uploadLessonKnowledge, deleteLessonKnowledge } from '@/api/teacher'
import { getCourseKnowledge, uploadCourseKnowledge, deleteCourseKnowledge } from '@/api/teacher'
import { uploadCover, uploadVideo } from '@/api/upload'
import type { ChapterItem, CourseKnowledgeItem, LessonItem, LessonKnowledgeItem, TeacherCourse, TeacherSeckill, TeacherSku } from '@/api/teacher'

const tab = ref('courses')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null
const form = ref({ title: '', category: '', description: '', cover: '', video_url: '', total_hours: 0, price: null as number | null, stock: 0 })

const courses = ref<TeacherCourse[]>([])
const loadingCourses = ref(true)
const totalCourses = computed(() => courses.value.length)
const creating = ref(false)

const sales = ref({ total_sales: '0.00', order_count: 0, hot_courses: [] as Array<{ id: number; title: string; sold: number }> })
const loadingSales = ref(true)

/* ===== Seckill ===== */
const seckillDialogVisible = ref(false)
const seckillCreating = ref(false)
const teacherSkus = ref<TeacherSku[]>([])
const seckills = ref<TeacherSeckill[]>([])
const loadingSeckills = ref(true)
const seckillForm = ref({
  sku_id: null as number | null,
  seckill_price: 0,
  stock: 10,
  limit_quantity: 1,
  start_time: '',
  end_time: '',
})

/* ===== Content Management ===== */
const contentCourseId = ref<number | null>(null)
const chapters = ref<ChapterItem[]>([])
const loadingContent = ref(false)

const chapterDialogVisible = ref(false)
const editingChapterId = ref<number | null>(null)
const chapterForm = ref({ title: '' })
const chapterSaving = ref(false)
const selectedChapterId = ref<number | null>(null)

const lessonDialogVisible = ref(false)
const editingLessonId = ref<number | null>(null)
const lessonForm = ref({ title: '', video_url: '', duration: 0, sort_order: 0 })
const lessonSaving = ref(false)

/* ===== Knowledge Base ===== */
const currentLessonId = ref<number | null>(null)
const knowledgeFiles = ref<LessonKnowledgeItem[]>([])
const knowledgeUploading = ref(false)

/* ===== Course Knowledge Base ===== */
const courseKnowledgeFiles = ref<CourseKnowledgeItem[]>([])
const courseKnowledgeUploading = ref(false)
const courseKnowledgeInputRef = ref<HTMLInputElement>()

/* ===== Pending Knowledge (for create — uploaded after course is saved) ===== */
const pendingKnowledgeFiles = ref<{ file: File; name: string; size: number }[]>([])

/* ===== File Input Refs ===== */
const coverInputRef = ref<HTMLInputElement>()
const videoInputRef = ref<HTMLInputElement>()
const courseVideoInputRef = ref<HTMLInputElement>()
const lessonKnowledgeInputRef = ref<HTMLInputElement>()

function triggerCoverInput() { coverInputRef.value?.click() }
function triggerVideoInput() { videoInputRef.value?.click() }
function triggerCourseVideoInput() { courseVideoInputRef.value?.click() }
function triggerLessonKnowledgeInput() { lessonKnowledgeInputRef.value?.click() }
function triggerCourseKnowledgeInput() { courseKnowledgeInputRef.value?.click() }

function onCoverFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  handleCoverUpload(file)
  ;(e.target as HTMLInputElement).value = ''
}

function onVideoFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  handleVideoUpload(file)
  ;(e.target as HTMLInputElement).value = ''
}

function onCourseVideoFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  handleCourseVideoUpload(file)
  ;(e.target as HTMLInputElement).value = ''
}

function onLessonKnowledgeFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  handleKnowledgeUpload(file)
  ;(e.target as HTMLInputElement).value = ''
}

function onCourseKnowledgeFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  handleCourseKnowledgeUpload(file)
  ;(e.target as HTMLInputElement).value = ''
}

async function loadKnowledge(lessonId: number) {
  currentLessonId.value = lessonId
  try {
    knowledgeFiles.value = await getLessonKnowledge(lessonId)
  } catch {
    knowledgeFiles.value = []
  }
}

async function handleKnowledgeUpload(file: File) {
  let lessonId = currentLessonId.value
  if (!lessonId) {
    // Lesson not saved yet — auto-save first
    if (!selectedChapterId.value) { ElMessage.warning('请先选择章节'); return }
    if (!lessonForm.value.title.trim()) { ElMessage.warning('请先填写课时名称'); return }
    lessonSaving.value = true
    try {
      const lesson = await createLesson(selectedChapterId.value, {
        title: lessonForm.value.title,
        video_url: lessonForm.value.video_url || null,
        duration: lessonForm.value.duration,
        sort_order: lessonForm.value.sort_order,
      })
      currentLessonId.value = lesson.id
      lessonId = lesson.id
      // Switch to edit mode so subsequent "添加" calls update instead of duplicate
      editingLessonId.value = lesson.id
      selectedChapterId.value = null
      ElMessage.success('课时已自动保存')
    } catch {
      return
    } finally {
      lessonSaving.value = false
    }
  }
  if (!lessonId) return
  knowledgeUploading.value = true
  try {
    const result = await uploadLessonKnowledge(lessonId, file)
    knowledgeFiles.value.unshift(result)
    ElMessage.success('文档上传成功')
  } catch {
    ElMessage.error('文档上传失败')
  } finally {
    knowledgeUploading.value = false
  }
}

async function handleDeleteKnowledge(kf: LessonKnowledgeItem) {
  const lessonId = currentLessonId.value
  if (!lessonId) return
  try {
    await ElMessageBox.confirm(`确定删除文档「${kf.file_name}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await deleteLessonKnowledge(lessonId, kf.id)
    knowledgeFiles.value = knowledgeFiles.value.filter((x) => x.id !== kf.id)
    ElMessage.success('文档已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

async function loadCourseKnowledge(courseId: number) {
  try {
    courseKnowledgeFiles.value = await getCourseKnowledge(courseId)
  } catch {
    courseKnowledgeFiles.value = []
  }
}

async function handleCourseKnowledgeUpload(file: File) {
  if (!editingId.value) {
    // Create mode: queue the file for upload after course is saved
    pendingKnowledgeFiles.value.push({ file, name: file.name, size: file.size })
    ElMessage.success(`「${file.name}」已加入待上传队列，保存课程后将自动上传`)
    return
  }
  courseKnowledgeUploading.value = true
  try {
    const result = await uploadCourseKnowledge(editingId.value, file)
    courseKnowledgeFiles.value.unshift(result)
    ElMessage.success('文档上传成功')
  } catch {
    ElMessage.error('文档上传失败')
  } finally {
    courseKnowledgeUploading.value = false
  }
}

async function handleCourseKnowledgeDelete(kf: CourseKnowledgeItem) {
  if (!editingId.value) return
  try {
    await ElMessageBox.confirm(`确定删除文档「${kf.file_name}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await deleteCourseKnowledge(editingId.value, kf.id)
    courseKnowledgeFiles.value = courseKnowledgeFiles.value.filter((x) => x.id !== kf.id)
    ElMessage.success('文档已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

function formatDuration(seconds: number) {
  if (!seconds) return ''
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s}秒`
  return `${m}分${s > 0 ? s + '秒' : ''}`
}

async function loadContent() {
  if (!contentCourseId.value) return
  loadingContent.value = true
  try {
    chapters.value = await getTeacherChapters(contentCourseId.value)
  } catch {
    chapters.value = []
  } finally {
    loadingContent.value = false
  }
}

function openChapterDialog() {
  editingChapterId.value = null
  chapterForm.value = { title: '' }
  chapterDialogVisible.value = true
}

function editChapter(chapter: ChapterItem) {
  editingChapterId.value = chapter.id
  chapterForm.value = { title: chapter.title }
  chapterDialogVisible.value = true
}

async function handleSaveChapter() {
  if (!chapterForm.value.title.trim()) { ElMessage.warning('请输入章节名称'); return }
  if (!contentCourseId.value) return
  chapterSaving.value = true
  try {
    if (editingChapterId.value) {
      await updateChapter(editingChapterId.value, { title: chapterForm.value.title })
      ElMessage.success('章节已更新')
    } else {
      await createChapter(contentCourseId.value, { title: chapterForm.value.title })
      ElMessage.success('章节已创建')
    }
    chapterDialogVisible.value = false
    await loadContent()
  } catch {
    // handled by interceptor
  } finally {
    chapterSaving.value = false
  }
}

async function handleDeleteChapter(chapter: ChapterItem) {
  try {
    await ElMessageBox.confirm(`确定删除章节「${chapter.title}」及其所有课时？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await deleteChapter(chapter.id)
    ElMessage.success('章节已删除')
    await loadContent()
  } catch {
    ElMessage.error('删除失败')
  }
}

function openLessonDialog(chapterId: number) {
  selectedChapterId.value = chapterId
  editingLessonId.value = null
  lessonForm.value = { title: '', video_url: '', duration: 0, sort_order: 0 }
  knowledgeFiles.value = []
  currentLessonId.value = null
  lessonDialogVisible.value = true
}

function editLesson(lesson: LessonItem) {
  selectedChapterId.value = null
  editingLessonId.value = lesson.id
  lessonForm.value = {
    title: lesson.title,
    video_url: lesson.video_url || '',
    duration: lesson.duration,
    sort_order: lesson.sort_order,
  }
  lessonDialogVisible.value = true
  loadKnowledge(lesson.id)
}

async function handleSaveLesson() {
  if (!lessonForm.value.title.trim()) { ElMessage.warning('请输入课时名称'); return }
  lessonSaving.value = true
  try {
    if (editingLessonId.value) {
      await updateLesson(editingLessonId.value, {
        title: lessonForm.value.title,
        video_url: lessonForm.value.video_url || null,
        duration: lessonForm.value.duration,
        sort_order: lessonForm.value.sort_order,
      })
      ElMessage.success('课时已更新')
    } else if (selectedChapterId.value) {
      const lesson = await createLesson(selectedChapterId.value, {
        title: lessonForm.value.title,
        video_url: lessonForm.value.video_url || null,
        duration: lessonForm.value.duration,
        sort_order: lessonForm.value.sort_order,
      })
      currentLessonId.value = lesson.id
      ElMessage.success('课时已添加')
    }
    await loadContent()
  } catch {
    // handled by interceptor
  } finally {
    lessonSaving.value = false
  }
}

async function handleDeleteLesson(lesson: LessonItem) {
  try {
    await ElMessageBox.confirm(`确定删除课时「${lesson.title}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await deleteLesson(lesson.id)
    ElMessage.success('课时已删除')
    await loadContent()
  } catch {
    ElMessage.error('删除失败')
  }
}

function formatAmount(value: string | number) {
  const num = typeof value === 'number' ? value : parseFloat(value || '0')
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function statusLabel(status: string) {
  return { draft: '草稿', pending: '待审核', published: '已发布', closed: '已下架' }[status] || status
}
function statusTagType(status: string): '' | 'success' | 'warning' | 'danger' {
  return (status === 'published' ? 'success' : status === 'pending' ? 'warning' : status === 'closed' ? 'danger' : '') as '' | 'success' | 'warning' | 'danger'
}

async function loadCourses() {
  loadingCourses.value = true
  try {
    const res = await listTeacherCourses({ page: 1, page_size: 50 })
    courses.value = res.items
  } catch {
    courses.value = []
  } finally {
    loadingCourses.value = false
  }
}

async function loadSales() {
  loadingSales.value = true
  try {
    sales.value = await getTeacherSales()
  } catch {
    sales.value = { total_sales: '0.00', order_count: 0, hot_courses: [] }
  } finally {
    loadingSales.value = false
  }
}

/* ===== Seckill ===== */
function seckillStatusLabel(status: string) {
  return { pending: '待审批', active: '已通过', finished: '已结束' }[status] || status
}
function seckillStatusType(status: string): '' | 'success' | 'warning' | 'info' {
  return (status === 'active' ? 'success' : status === 'pending' ? 'warning' : 'info') as '' | 'success' | 'warning' | 'info'
}
function formatSeckillDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return dateStr
  }
}
async function loadTeacherSkus() {
  try {
    teacherSkus.value = await listTeacherSkus()
  } catch {
    teacherSkus.value = []
  }
}
async function loadSeckills() {
  loadingSeckills.value = true
  try {
    const res = await listTeacherSeckills({ page: 1, page_size: 50 })
    seckills.value = res.items
  } catch {
    seckills.value = []
  } finally {
    loadingSeckills.value = false
  }
}
function openSeckillDialog() {
  seckillForm.value = { sku_id: null, seckill_price: 0, stock: 10, limit_quantity: 1, start_time: '', end_time: '' }
  loadTeacherSkus()
  seckillDialogVisible.value = true
}
async function handleCreateSeckill() {
  if (!seckillForm.value.sku_id) { ElMessage.warning('请选择课程 SKU'); return }
  if (!seckillForm.value.start_time || !seckillForm.value.end_time) { ElMessage.warning('请选择活动时间范围'); return }
  if (seckillForm.value.seckill_price <= 0) { ElMessage.warning('秒杀价必须大于 0'); return }
  seckillCreating.value = true
  try {
    await createTeacherSeckill({
      sku_id: seckillForm.value.sku_id,
      seckill_price: seckillForm.value.seckill_price,
      stock: seckillForm.value.stock,
      limit_quantity: seckillForm.value.limit_quantity,
      start_time: seckillForm.value.start_time,
      end_time: seckillForm.value.end_time,
    })
    ElMessage.success('秒杀申请已提交，等待管理员审批')
    seckillDialogVisible.value = false
    await loadSeckills()
  } catch {
    // error handled by interceptor
  } finally {
    seckillCreating.value = false
  }
}

/* ===== File Upload ===== */

async function handleCoverUpload(file: File) {
  try {
    const result = await uploadCover(file)
    form.value.cover = result.url
    ElMessage.success('封面上传成功')
  } catch {
    ElMessage.error('封面上传失败')
  }
}

async function handleVideoUpload(file: File) {
  try {
    const result = await uploadVideo(file)
    lessonForm.value.video_url = result.url
    // Auto-populate title from filename if title is empty
    if (!lessonForm.value.title.trim()) {
      const name = file.name.replace(/\.[^.]+$/, '')
      lessonForm.value.title = name
    }
    ElMessage.success('视频上传成功')
  } catch {
    ElMessage.error('视频上传失败')
  }
}

async function handleCourseVideoUpload(file: File) {
  try {
    const result = await uploadVideo(file)
    form.value.video_url = result.url
    // Auto-detect video duration and set total_hours (in hours, rounded to 1 decimal)
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.onloadedmetadata = () => {
      const durationSec = video.duration || 0
      form.value.total_hours = Math.round(durationSec / 3600) || 0
    }
    video.src = result.url
    ElMessage.success('视频上传成功')
  } catch {
    ElMessage.error('视频上传失败')
  }
}

async function handleSave() {
  if (!form.value.title.trim()) { ElMessage.warning('请填写课程标题'); return }
  if (!form.value.category.trim()) { ElMessage.warning('请填写课程分类'); return }
  if (!form.value.description.trim()) { ElMessage.warning('请填写课程简介'); return }
  if (form.value.price === null || form.value.price < 0) { ElMessage.warning('请设置课程价格'); return }
  if (editingId.value) {
    // Edit mode: require at least one existing knowledge file
    if (courseKnowledgeFiles.value.length === 0 && pendingKnowledgeFiles.value.length === 0) {
      ElMessage.warning('请至少上传一份知识库文档')
      return
    }
  } else {
    // Create mode: require at least one knowledge file (pending or already uploaded somehow)
    if (pendingKnowledgeFiles.value.length === 0 && courseKnowledgeFiles.value.length === 0) {
      ElMessage.warning('请至少选择一份知识库文档')
      return
    }
  }
  creating.value = true
  try {
    if (editingId.value) {
      await updateCourse(editingId.value, form.value)
      // Upload any pending knowledge files for edit mode too
      for (const pf of pendingKnowledgeFiles.value) {
        await uploadCourseKnowledge(editingId.value, pf.file)
      }
      pendingKnowledgeFiles.value = []
      ElMessage.success('已保存修改')
    } else {
      const course = await createCourse(form.value)
      const courseId = course.id
      // Upload pending knowledge files
      for (const pf of pendingKnowledgeFiles.value) {
        try {
          const result = await uploadCourseKnowledge(courseId, pf.file)
          courseKnowledgeFiles.value.unshift(result)
        } catch {
          ElMessage.error(`知识库文档「${pf.name}」上传失败`)
        }
      }
      pendingKnowledgeFiles.value = []
      ElMessage.success('课程已创建')
    }
    dialogVisible.value = false
    await loadCourses()
  } finally {
    creating.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { title: '', category: '', description: '', cover: '', video_url: '', total_hours: 0, price: null, stock: 0 }
  courseKnowledgeFiles.value = []
  pendingKnowledgeFiles.value = []
  dialogVisible.value = true
}

function openEdit(row: TeacherCourse) {
  editingId.value = row.id
  form.value = {
    title: row.title,
    category: row.category || '',
    description: row.description || '',
    cover: row.cover || '',
    total_hours: row.total_hours ?? 0,
    price: row.price !== null && row.price !== undefined ? Number(row.price) : null,
    stock: row.stock ?? 0,
    video_url: (row as any).video_url || '',
  }
  pendingKnowledgeFiles.value = []
  loadCourseKnowledge(row.id)
  dialogVisible.value = true
}

async function handleClose(course: TeacherCourse) {
  try {
    await ElMessageBox.confirm(`确定下架《${course.title}》吗？下架后学员将无法购买此课程。`, '下架确认', { type: 'warning' })
  } catch { return }
  try {
    await closeCourse(course.id)
    ElMessage.success('已下架')
    await loadCourses()
  } catch {
    ElMessage.error('下架失败')
  }
}

async function handleSubmit(course: TeacherCourse) {
  try {
    await submitCourse(course.id)
    ElMessage.success('已提交审核')
    await loadCourses()
  } catch {
    ElMessage.error('提交失败')
  }
}

function renderChart() {
  if (!chartRef.value) return
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  chartInstance = echarts.init(chartRef.value)
  const hot = sales.value.hot_courses
  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    color: ['#e65100'],
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: hot.length ? hot.map((h) => h.title) : ['暂无数据'], axisLabel: { interval: 0, rotate: 30 } },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: hot.length ? hot.map((h) => h.sold) : [0],
      barWidth: 32,
      itemStyle: { borderRadius: [8, 8, 0, 0], color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: '#ff9800' },
        { offset: 1, color: '#e65100' },
      ])}
    }],
  })
}

watch(tab, async (v) => {
  if (v === 'sales') {
    await loadSales()
    await nextTick()
    renderChart()
  }
})
onMounted(() => {
  loadCourses()
  loadSeckills()
  loadSales().then(() => { if (tab.value === 'sales') nextTick(() => renderChart()) })
})
onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.teacher-dashboard {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 32px var(--gutter);
}

/* ===== Header ===== */
.teacher-header {
  position: relative;
  border-radius: var(--radius-xl);
  overflow: hidden;
  margin-bottom: 28px;
  padding: 36px 40px;
  background: linear-gradient(135deg, #e65100 0%, #f57c00 50%, #ff9800 100%);
  color: #fff;
}
.teacher-header-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(255, 152, 0, 0.4) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(230, 81, 0, 0.3) 0%, transparent 50%);
  pointer-events: none;
}
.teacher-header-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.teacher-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.teacher-icon {
  font-size: 40px;
  background: rgba(255,255,255,0.15);
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.teacher-icon .material-symbols-outlined {
  font-size: 32px;
  color: #fff;
}
.teacher-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.01em;
}
.teacher-subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: rgba(255,255,255,0.8);
}

/* ===== Stats Cards ===== */
.teacher-stats {
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
.stat-orange .stat-icon-wrap { background: linear-gradient(135deg, #e65100, #f57c00); }
.stat-gold .stat-icon-wrap { background: linear-gradient(135deg, #f9a825, #fdd835); }
.stat-teal .stat-icon-wrap { background: linear-gradient(135deg, #00796b, #009688); }
.stat-emerald .stat-icon-wrap { background: linear-gradient(135deg, #2e7d32, #43a047); }

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

/* ===== Panel & Tabs ===== */
.teacher-panel {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-xl);
  box-shadow: var(--elev-1);
  overflow: hidden;
}
.teacher-tabs :deep(.el-tabs__header) {
  margin: 0;
  background: var(--surface-container-low);
  border-bottom: 1px solid var(--outline-variant);
  padding: 0 16px;
}
.teacher-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  height: 52px;
  line-height: 52px;
}
.teacher-tabs :deep(.el-tabs__active-bar) {
  background: #e65100;
  height: 3px;
  bottom: 0;
}
.teacher-tabs :deep(.el-tabs__content) {
  padding: 24px;
}

.tab-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.styled-table {
  margin-top: 8px;
}

.chart {
  height: 380px;
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.empty-mini {
  text-align: center;
  padding: 40px 0;
  color: var(--on-surface-variant);
  font-size: 14px;
}

.hot-list {
  margin-top: 20px;
  padding: 20px;
  background: linear-gradient(135deg, var(--surface-container-lowest), var(--surface-container-low));
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
}
.hot-title {
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 600;
  color: var(--on-surface);
  display: flex;
  align-items: center;
  gap: 6px;
}
.hot-title .material-symbols-outlined {
  font-size: 20px;
  color: #f9a825;
}
.hot-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px dashed var(--outline-variant);
}
.hot-row:last-child { border-bottom: none; }
.hot-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.hot-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 800;
  color: #fff;
}
.rank-1 { background: linear-gradient(135deg, #f9a825, #fdd835); }
.rank-2 { background: linear-gradient(135deg, #90a4ae, #b0bec5); }
.rank-3 { background: linear-gradient(135deg, #a1887f, #bcaaa4); }
.hot-name { color: var(--on-surface); font-weight: 500; }
.hot-sold {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #e65100;
  font-weight: 600;
  font-size: 14px;
}

/* ===== Content Management ===== */
.content-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}
.content-chapter {
  background: var(--surface-container-low);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.content-chapter-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--surface-container);
  border-bottom: 1px solid var(--outline-variant);
}
.content-chapter-title {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  color: var(--on-surface);
}
.content-chapter-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.content-lessons { padding: 4px 0; }
.content-lesson-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px 8px 32px;
  font-size: 14px;
  transition: background 0.15s;
}
.content-lesson-item:hover { background: var(--surface-container-lowest); }
.content-lesson-icon .material-symbols-outlined { font-size: 18px; color: var(--primary); }
.content-lesson-title { flex: 1; color: var(--on-surface); }
.content-lesson-duration { font-size: 12px; color: var(--on-surface-variant); }
.content-lesson-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s;
}
.content-lesson-item:hover .content-lesson-actions { opacity: 1; }

/* ===== Upload ===== */
.cover-upload-wrap, .video-upload-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cover-preview {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: var(--radius);
  border: 1px solid var(--outline-variant);
}
.video-preview {
  width: 100%;
  max-height: 200px;
  border-radius: var(--radius);
  border: 1px solid var(--outline-variant);
  background: #000;
}
.cover-hint {
  font-size: 12px;
  color: var(--on-surface-variant);
}

@media (max-width: 960px) {
  .teacher-stats { grid-template-columns: repeat(2, 1fr); }
  .teacher-header { padding: 24px 20px; }
  .teacher-header-content { flex-direction: column; align-items: flex-start; gap: 12px; }
}
@media (max-width: 600px) {
  .teacher-stats { grid-template-columns: 1fr; }
}

/* ── Knowledge Base ── */
.knowledge-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.knowledge-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.knowledge-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--surface-container-high);
  border-radius: var(--radius);
}
.kf-icon {
  font-size: 20px;
  color: var(--primary);
}
.kf-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.kf-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kf-meta {
  font-size: 11px;
  color: var(--on-surface-variant);
}
.knowledge-pending {
  opacity: 0.7;
  border: 1px dashed var(--outline-variant);
}
.knowledge-pending .kf-icon {
  color: var(--warning);
}
</style>
