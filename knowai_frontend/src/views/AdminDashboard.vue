<template>
  <div class="admin-dashboard">
    <!-- Header with gradient -->
    <div class="admin-header">
      <div class="admin-header-bg"></div>
      <div class="admin-header-content">
        <div class="admin-header-left">
          <span class="admin-icon"><span class="material-symbols-outlined">shield</span></span>
          <div>
            <h1 class="admin-title">管理后台</h1>
            <p class="admin-subtitle">系统管理与监控中心</p>
          </div>
        </div>
        <div class="admin-header-right">
          <el-tag effect="dark" round type="success">
            <span class="material-symbols-outlined" style="font-size:14px;vertical-align:middle">check_circle</span> 系统运行中
          </el-tag>
        </div>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="admin-stats">
      <div class="stat-card stat-blue">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">group</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ stats.total_users }}</p>
          <p class="stat-label">注册用户</p>
        </div>
      </div>
      <div class="stat-card stat-purple">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">menu_book</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ stats.active_courses }}</p>
          <p class="stat-label">上架课程</p>
        </div>
      </div>
      <div class="stat-card stat-orange">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">pending_actions</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ stats.pending_courses }}</p>
          <p class="stat-label">待审课程</p>
        </div>
      </div>
      <div class="stat-card stat-red">
        <div class="stat-icon-wrap"><span class="material-symbols-outlined">local_fire_department</span></div>
        <div class="stat-info">
          <p class="stat-value">{{ stats.pending_seckills }}</p>
          <p class="stat-label">待审秒杀</p>
        </div>
      </div>
    </div>

    <!-- Tab Panel -->
    <div class="admin-panel">
      <el-tabs v-model="tab" class="admin-tabs">
        <el-tab-pane label="👥 用户管理" name="users">
          <el-table :data="users" class="styled-table" v-loading="loadingUsers" stripe>
            <el-table-column prop="username" label="用户名" width="140" />
            <el-table-column prop="email" label="邮箱" min-width="200" />
            <el-table-column label="角色" width="100">
              <template #default="{ row }">
                <el-tag effect="light" round size="small" :type="row.role === 'admin' ? 'danger' : row.role === 'teacher' ? 'warning' : 'info'">
                  {{ roleLabel(row.role) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'" effect="light" round size="small">
                  {{ row.is_active ? '正常' : '封禁' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="200">
              <template #default="{ row }">
                <el-button link :type="row.is_active ? 'danger' : 'success'" @click="toggleUserStatus(row)">
                  {{ row.is_active ? '封禁' : '解封' }}
                </el-button>
                <el-button link type="danger" @click="handleDeleteUser(row)">注销</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="📚 课程审核" name="courses">
          <el-table :data="pendingCourses" class="styled-table" v-loading="loadingCourses" stripe>
            <el-table-column prop="title" label="课程名称" min-width="200" />
            <el-table-column prop="teacher_name" label="讲师" width="120" />
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column label="操作" width="260">
              <template #default="{ row }">
                <el-button link type="primary" @click="showCourseDetail(row)">查看详情</el-button>
                <el-button link type="success" @click="approveCourseAction(row)">✓ 通过</el-button>
                <el-button link type="danger" @click="rejectCourseAction(row)">✗ 驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="⚡ 秒杀审批" name="seckills">
          <el-table :data="pendingSeckills" class="styled-table" v-loading="loadingSeckills" stripe>
            <el-table-column label="活动 ID" prop="id" width="80" />
            <el-table-column label="秒杀价" width="100">
              <template #default="{ row }">¥{{ row.seckill_price }}</template>
            </el-table-column>
            <el-table-column prop="stock" label="库存" width="80" />
            <el-table-column label="时间范围" min-width="220">
              <template #default="{ row }">{{ formatDate(row.start_time) }} ~ {{ formatDate(row.end_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="220">
              <template #default="{ row }">
                <el-button link type="primary" @click="showSeckillDetail(row)">查看详情</el-button>
                <el-button link type="primary" @click="approveSeckillAction(row)">审批通过</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="👨‍🏫 讲师审核" name="teachers">
          <el-table :data="pendingTeachers" class="styled-table" v-loading="loadingTeachers" stripe>
            <el-table-column prop="username" label="用户名" width="120" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="phone" label="手机号" width="130" />
            <el-table-column prop="email" label="邮箱" min-width="180" />
            <el-table-column prop="bio" label="简介" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="260">
              <template #default="{ row }">
                <el-button link type="primary" @click="showTeacherDetail(row)">查看详情</el-button>
                <el-button link type="success" @click="approveTeacherAction(row)">✓ 通过</el-button>
                <el-button link type="danger" @click="rejectTeacherAction(row)">✗ 拒绝</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="📋 所有课程" name="all-courses">
          <div class="tab-toolbar">
            <el-input v-model="courseKeyword" placeholder="搜索课程..." clearable style="width:260px" size="large" @clear="loadAllCourses" @keyup.enter="loadAllCourses" />
            <el-select v-model="courseStatusFilter" placeholder="全部状态" clearable size="large" style="width:140px" @change="loadAllCourses">
              <el-option label="已发布" value="published" />
              <el-option label="待审核" value="pending" />
              <el-option label="草稿" value="draft" />
              <el-option label="已下架" value="closed" />
            </el-select>
            <el-button type="primary" size="large" @click="openCourseDialog(null)">
              <span class="material-symbols-outlined">add</span> 新增课程
            </el-button>
          </div>
          <el-table :data="allCourses" class="styled-table" v-loading="loadingAllCourses" stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="title" label="课程名称" min-width="180" />
            <el-table-column prop="teacher_name" label="讲师" width="120" />
            <el-table-column label="评分" width="100">
              <template #default="{ row }">
                <el-rate v-model="row.rating" disabled :max="5" show-score score-template="{value}" />
              </template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" effect="light" round size="small">
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-button link type="warning" @click="openCourseDialog(row)">编辑</el-button>
                <el-button v-if="row.status !== 'closed'" link type="danger" @click="handleDeleteCourse(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="coursePage"
              v-model:page-size="coursePageSize"
              :total="courseTotal"
              layout="total, prev, pager, next"
              @current-change="loadAllCourses"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane label="💬 评论管理" name="reviews">
          <el-table :data="allReviews" class="styled-table" v-loading="loadingReviews" stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="course_title" label="课程" min-width="160" show-overflow-tooltip />
            <el-table-column prop="username" label="用户" width="120" />
            <el-table-column label="评分" width="140">
              <template #default="{ row }">
                <el-rate v-model="row.rating" disabled :max="5" />
              </template>
            </el-table-column>
            <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
            <el-table-column label="时间" width="140">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button link type="danger" @click="handleDeleteReview(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="reviewPage"
              v-model:page-size="reviewPageSize"
              :total="reviewTotal"
              layout="total, prev, pager, next"
              @current-change="loadAllReviews"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- Course Create/Edit Dialog -->
    <el-dialog v-model="courseDialogVisible" :title="editingCourseId ? '编辑课程' : '新增课程'" width="560px" class="styled-dialog">
      <el-form label-position="top">
        <el-form-item label="讲师">
          <el-select v-model="courseForm.teacher_id" placeholder="选择讲师" size="large" style="width:100%" :disabled="!!editingCourseId">
            <el-option v-for="t in teacherOptions" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程标题">
          <el-input v-model="courseForm.title" size="large" placeholder="请输入课程标题" />
        </el-form-item>
        <el-form-item label="课程分类">
          <el-input v-model="courseForm.category" size="large" placeholder="如：AI / Python / 前端" />
        </el-form-item>
        <el-form-item label="课程简介">
          <el-input v-model="courseForm.description" type="textarea" :rows="3" placeholder="课程简介..." />
        </el-form-item>
        <el-form-item label="总时长（小时）">
          <el-input-number v-model="courseForm.total_hours" :min="0" :max="500" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="courseSaving" @click="handleSaveCourse">{{ editingCourseId ? '保存修改' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- Teacher Detail Dialog -->
    <el-dialog v-model="teacherDetailVisible" title="讲师申请详情" width="560px" class="styled-dialog">
      <template v-if="teacherDetail">
        <div class="detail-section">
          <div class="detail-avatar" v-if="teacherDetail.avatar">
            <img :src="teacherDetail.avatar" alt="avatar" />
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户名">{{ teacherDetail.username }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ teacherDetail.name }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ teacherDetail.phone }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ teacherDetail.email }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag effect="light" round size="small" type="warning">待审批</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="申请时间">{{ formatDate(teacherDetail.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="个人简介" :span="2">
              {{ teacherDetail.bio || '未填写' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </template>
      <template #footer>
        <el-button @click="teacherDetailVisible = false">关闭</el-button>
        <el-button type="success" :loading="detailApproving" @click="approveTeacherFromDetail">✓ 通过</el-button>
        <el-button type="danger" :loading="detailRejecting" @click="rejectTeacherFromDetail">✗ 拒绝</el-button>
      </template>
    </el-dialog>

    <!-- Course Detail Dialog -->
    <el-dialog v-model="courseDetailVisible" title="课程审核详情" width="700px" class="styled-dialog">
      <template v-if="courseDetail">
        <div class="detail-section">
          <div class="detail-cover" v-if="courseDetail.cover">
            <img :src="courseDetail.cover" alt="cover" />
          </div>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="课程名称" :span="2">{{ courseDetail.title }}</el-descriptions-item>
            <el-descriptions-item label="讲师">{{ courseDetail.teacher_name }}</el-descriptions-item>
            <el-descriptions-item label="分类">{{ courseDetail.category || '未设置' }}</el-descriptions-item>
            <el-descriptions-item label="总时长">{{ courseDetail.total_hours }} 小时</el-descriptions-item>
            <el-descriptions-item label="学习人数">{{ courseDetail.learn_count }}</el-descriptions-item>
          </el-descriptions>
          <h4 class="detail-subtitle">课程简介</h4>
          <p class="detail-text">{{ courseDetail.description || '暂无简介' }}</p>

          <h4 class="detail-subtitle">定价信息</h4>
          <el-table :data="courseDetail.skus" size="small" stripe>
            <el-table-column prop="sku_name" label="SKU 名称" />
            <el-table-column label="价格">
              <template #default="{ row }">¥{{ row.price }}</template>
            </el-table-column>
            <el-table-column prop="stock" label="库存" />
          </el-table>

          <h4 class="detail-subtitle">课程章节（{{ courseDetail.chapters.length }} 章）</h4>
          <div v-if="courseDetail.chapters.length" class="detail-chapters">
            <div v-for="ch in courseDetail.chapters" :key="ch.id" class="detail-chapter">
              <div class="detail-chapter-title">{{ ch.sort_order }}. {{ ch.title }}</div>
              <div v-if="ch.lessons.length" class="detail-lessons">
                <div v-for="le in ch.lessons" :key="le.id" class="detail-lesson">
                  <span class="material-symbols-outlined" style="font-size:16px">play_circle</span>
                  {{ le.title }}
                  <span class="detail-lesson-duration">{{ le.duration }}秒</span>
                </div>
              </div>
              <div v-else class="detail-empty">暂无课时</div>
            </div>
          </div>
          <div v-else class="detail-empty">暂无章节</div>

          <h4 v-if="courseDetail.knowledge_files?.length" class="detail-subtitle">知识库文档（{{ courseDetail.knowledge_files.length }} 个）</h4>
          <div v-if="courseDetail.knowledge_files?.length" class="detail-knowledge-list">
            <div v-for="kf in courseDetail.knowledge_files" :key="kf.id" class="detail-knowledge-item">
              <span class="material-symbols-outlined" style="font-size:16px">description</span>
              {{ kf.file_name }}
              <span class="detail-lesson-duration">{{ (kf.file_size / 1024).toFixed(1) }} KB</span>
            </div>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button @click="courseDetailVisible = false">关闭</el-button>
        <el-button type="success" :loading="detailApproving" @click="approveCourseFromDetail">✓ 通过</el-button>
        <el-button type="danger" :loading="detailRejecting" @click="rejectCourseFromDetail">✗ 驳回</el-button>
      </template>
    </el-dialog>

    <!-- Seckill Detail Dialog -->
    <el-dialog v-model="seckillDetailVisible" title="秒杀活动详情" width="560px" class="styled-dialog">
      <template v-if="seckillDetail">
        <div class="detail-section">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="活动 ID" :span="2">{{ seckillDetail.id }}</el-descriptions-item>
            <el-descriptions-item label="关联课程" :span="2">{{ seckillDetail.course_title || '未知课程' }}</el-descriptions-item>
            <el-descriptions-item label="SKU 名称">{{ seckillDetail.sku_name || '默认' }}</el-descriptions-item>
            <el-descriptions-item label="SKU 库存">{{ seckillDetail.sku_stock }}</el-descriptions-item>
            <el-descriptions-item label="原价">¥{{ seckillDetail.sku_price }}</el-descriptions-item>
            <el-descriptions-item label="秒杀价">¥{{ seckillDetail.seckill_price }}</el-descriptions-item>
            <el-descriptions-item label="秒杀库存">{{ seckillDetail.stock }}</el-descriptions-item>
            <el-descriptions-item label="每人限购">{{ seckillDetail.limit_quantity }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ formatDate(seckillDetail.start_time) }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ formatDate(seckillDetail.end_time) }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag effect="light" round size="small" type="warning">待审批</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <div class="detail-price-compare">
            <span class="compare-original">原价: ¥{{ seckillDetail.sku_price }}</span>
            <span class="compare-arrow">→</span>
            <span class="compare-seckill">秒杀价: ¥{{ seckillDetail.seckill_price }}</span>
            <span class="compare-discount" v-if="Number(seckillDetail.sku_price) > 0">
              （{{ (100 - Number(seckillDetail.seckill_price) / Number(seckillDetail.sku_price) * 100).toFixed(0) }}% OFF）
            </span>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button @click="seckillDetailVisible = false">关闭</el-button>
        <el-button type="primary" :loading="detailApproving" @click="approveSeckillFromDetail">审批通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  adminCreateCourse,
  adminDeleteCourse,
  adminDeleteReview,
  adminDeleteUser,
  adminUpdateCourse,
  approveCourse,
  approveSeckill,
  approveTeacher,
  getDashboard,
  getCourseDetail,
  getSeckillDetail,
  getTeacherDetail,
  listAdminUsers,
  listAllCourses,
  listAllReviews,
  listAllTeachers,
  listPendingCourses,
  listPendingSeckills,
  listPendingTeachers,
  rejectCourse,
  rejectTeacher,
  updateUserStatus,
  type AdminCourse,
  type AdminCourseApproval,
  type AdminCourseDetail,
  type AdminReview,
  type AdminSeckillApproval,
  type AdminSeckillDetail,
  type AdminTeacherApproval,
  type AdminTeacherDetail,
  type AdminUser,
  type DashboardStats,
} from '@/api/admin'

const tab = ref('users')

const stats = ref<DashboardStats>({
  total_users: 0,
  today_registrations: 0,
  total_teachers: 0,
  pending_teachers: 0,
  active_courses: 0,
  pending_courses: 0,
  pending_seckills: 0,
})

const users = ref<AdminUser[]>([])
const loadingUsers = ref(true)
const pendingCourses = ref<AdminCourseApproval[]>([])
const loadingCourses = ref(true)
const pendingSeckills = ref<AdminSeckillApproval[]>([])
const loadingSeckills = ref(true)
const pendingTeachers = ref<AdminTeacherApproval[]>([])
const loadingTeachers = ref(true)

const roleLabels: Record<string, string> = { admin: '管理员', teacher: '讲师', student: '学生' }
function roleLabel(role: string) { return roleLabels[role] || role }

function formatDate(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch {
    return dateStr
  }
}

function statusLabel(status: string) {
  return { draft: '草稿', pending: '待审核', published: '已发布', closed: '已下架' }[status] || status
}
function statusTagType(status: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  return (status === 'published' ? 'success' : status === 'pending' ? 'warning' : status === 'closed' ? 'danger' : '') as '' | 'success' | 'warning' | 'danger' | 'info'
}

/* ===== Course Management ===== */
const allCourses = ref<AdminCourse[]>([])
const loadingAllCourses = ref(false)
const coursePage = ref(1)
const coursePageSize = ref(20)
const courseTotal = ref(0)
const courseKeyword = ref('')
const courseStatusFilter = ref('')

const teacherOptions = ref<Array<{ id: number; name: string }>>([])
const courseDialogVisible = ref(false)
const editingCourseId = ref<number | null>(null)
const courseForm = ref({ teacher_id: null as number | null, title: '', category: '', description: '', total_hours: 0 })
const courseSaving = ref(false)

/* ===== Detail Dialogs ===== */
const teacherDetailVisible = ref(false)
const teacherDetail = ref<AdminTeacherDetail | null>(null)
const teacherDetailTarget = ref<AdminTeacherApproval | null>(null)
const courseDetailVisible = ref(false)
const courseDetail = ref<AdminCourseDetail | null>(null)
const courseDetailTarget = ref<AdminCourseApproval | null>(null)
const seckillDetailVisible = ref(false)
const seckillDetail = ref<AdminSeckillDetail | null>(null)
const seckillDetailTarget = ref<AdminSeckillApproval | null>(null)
const detailApproving = ref(false)
const detailRejecting = ref(false)

async function showTeacherDetail(row: AdminTeacherApproval) {
  teacherDetailTarget.value = row
  try {
    teacherDetail.value = await getTeacherDetail(row.id)
    teacherDetailVisible.value = true
  } catch {
    ElMessage.error('获取讲师详情失败')
  }
}

async function showCourseDetail(row: AdminCourseApproval) {
  courseDetailTarget.value = row
  try {
    courseDetail.value = await getCourseDetail(row.id)
    courseDetailVisible.value = true
  } catch {
    ElMessage.error('获取课程详情失败')
  }
}

async function showSeckillDetail(row: AdminSeckillApproval) {
  seckillDetailTarget.value = row
  try {
    seckillDetail.value = await getSeckillDetail(row.id)
    seckillDetailVisible.value = true
  } catch {
    ElMessage.error('获取秒杀详情失败')
  }
}

async function approveTeacherFromDetail() {
  if (!teacherDetailTarget.value) return
  detailApproving.value = true
  try {
    await approveTeacher(teacherDetailTarget.value.id)
    ElMessage.success('讲师已通过审核')
    teacherDetailVisible.value = false
    pendingTeachers.value = pendingTeachers.value.filter((t) => t.id !== teacherDetailTarget.value!.id)
    stats.value.pending_teachers = Math.max(0, stats.value.pending_teachers - 1)
  } catch {
    ElMessage.error('操作失败')
  } finally {
    detailApproving.value = false
  }
}

async function rejectTeacherFromDetail() {
  if (!teacherDetailTarget.value) return
  detailRejecting.value = true
  try {
    await rejectTeacher(teacherDetailTarget.value.id)
    ElMessage.success('讲师已拒绝')
    teacherDetailVisible.value = false
    pendingTeachers.value = pendingTeachers.value.filter((t) => t.id !== teacherDetailTarget.value!.id)
    stats.value.pending_teachers = Math.max(0, stats.value.pending_teachers - 1)
  } catch {
    ElMessage.error('操作失败')
  } finally {
    detailRejecting.value = false
  }
}

async function approveCourseFromDetail() {
  if (!courseDetailTarget.value) return
  detailApproving.value = true
  try {
    await approveCourse(courseDetailTarget.value.id)
    ElMessage.success('已通过审核')
    courseDetailVisible.value = false
    pendingCourses.value = pendingCourses.value.filter((c) => c.id !== courseDetailTarget.value!.id)
    stats.value.pending_courses = Math.max(0, stats.value.pending_courses - 1)
  } catch {
    ElMessage.error('操作失败')
  } finally {
    detailApproving.value = false
  }
}

async function rejectCourseFromDetail() {
  if (!courseDetailTarget.value) return
  detailRejecting.value = true
  try {
    await rejectCourse(courseDetailTarget.value.id)
    ElMessage.success('已驳回')
    courseDetailVisible.value = false
    pendingCourses.value = pendingCourses.value.filter((c) => c.id !== courseDetailTarget.value!.id)
    stats.value.pending_courses = Math.max(0, stats.value.pending_courses - 1)
  } catch {
    ElMessage.error('操作失败')
  } finally {
    detailRejecting.value = false
  }
}

async function approveSeckillFromDetail() {
  if (!seckillDetailTarget.value) return
  detailApproving.value = true
  try {
    await approveSeckill(seckillDetailTarget.value.id)
    ElMessage.success('审批通过')
    seckillDetailVisible.value = false
    pendingSeckills.value = pendingSeckills.value.filter((s) => s.id !== seckillDetailTarget.value!.id)
    stats.value.pending_seckills = Math.max(0, stats.value.pending_seckills - 1)
  } catch {
    ElMessage.error('操作失败')
  } finally {
    detailApproving.value = false
  }
}

async function loadAllCourses() {
  loadingAllCourses.value = true
  try {
    const params: Record<string, unknown> = { page: coursePage.value, page_size: coursePageSize.value }
    if (courseKeyword.value) params.keyword = courseKeyword.value
    if (courseStatusFilter.value) params.status = courseStatusFilter.value
    const res = await listAllCourses(params)
    allCourses.value = res.items
    courseTotal.value = res.total
  } catch {
    allCourses.value = []
  } finally {
    loadingAllCourses.value = false
  }
}

async function openCourseDialog(course: AdminCourse | null) {
  // Load teacher list for both create and edit
  try { teacherOptions.value = await listAllTeachers() } catch { teacherOptions.value = [] }
  editingCourseId.value = course?.id ?? null
  courseForm.value = {
    teacher_id: course?.teacher_id ?? null,
    title: course?.title ?? '',
    category: course?.category ?? '',
    description: course?.description ?? '',
    total_hours: course?.total_hours ?? 0,
  }
  courseDialogVisible.value = true
}

async function handleSaveCourse() {
  if (!courseForm.value.title.trim()) { ElMessage.warning('请填写课程标题'); return }
  if (!editingCourseId.value && !courseForm.value.teacher_id) { ElMessage.warning('请选择讲师'); return }
  courseSaving.value = true
  try {
    if (editingCourseId.value) {
      await adminUpdateCourse(editingCourseId.value, courseForm.value)
      ElMessage.success('课程已更新')
    } else {
      await adminCreateCourse(courseForm.value as unknown as Record<string, unknown>)
      ElMessage.success('课程已创建')
    }
    courseDialogVisible.value = false
    await loadAllCourses()
  } catch {
    // handled by interceptor
  } finally {
    courseSaving.value = false
  }
}

async function handleDeleteCourse(course: AdminCourse) {
  try {
    await ElMessageBox.confirm(`确定删除课程「${course.title}」？将下架该课程，但已购买用户不受影响。`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await adminDeleteCourse(course.id)
    ElMessage.success('课程已删除（下架）')
    await loadAllCourses()
  } catch {
    ElMessage.error('删除失败')
  }
}

/* ===== Review Management ===== */
const allReviews = ref<AdminReview[]>([])
const loadingReviews = ref(false)
const reviewPage = ref(1)
const reviewPageSize = ref(20)
const reviewTotal = ref(0)

async function loadAllReviews() {
  loadingReviews.value = true
  try {
    const res = await listAllReviews({ page: reviewPage.value, page_size: reviewPageSize.value })
    allReviews.value = res.items
    reviewTotal.value = res.total
  } catch {
    allReviews.value = []
  } finally {
    loadingReviews.value = false
  }
}

async function handleDeleteReview(row: AdminReview) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」对课程「${row.course_title}」的评论？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await adminDeleteReview(row.id)
    ElMessage.success('评论已删除')
    await loadAllReviews()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function loadDashboard() {
  try { stats.value = await getDashboard() } catch { /* ignore */ }
}

async function loadUsers() {
  loadingUsers.value = true
  try {
    const res = await listAdminUsers({ page: 1, page_size: 50 })
    users.value = res.items
  } catch {
    users.value = []
  } finally {
    loadingUsers.value = false
  }
}

async function loadPendingCourses() {
  loadingCourses.value = true
  try {
    const res = await listPendingCourses({ page: 1, page_size: 50 })
    pendingCourses.value = res.items
  } catch {
    pendingCourses.value = []
  } finally {
    loadingCourses.value = false
  }
}

async function loadPendingSeckills() {
  loadingSeckills.value = true
  try {
    const res = await listPendingSeckills({ page: 1, page_size: 50 })
    pendingSeckills.value = res.items
  } catch {
    pendingSeckills.value = []
  } finally {
    loadingSeckills.value = false
  }
}

async function toggleUserStatus(row: AdminUser) {
  try {
    await updateUserStatus(row.id, !row.is_active)
    row.is_active = !row.is_active
    ElMessage.success(row.is_active ? '已解封' : '已封禁')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleDeleteUser(row: AdminUser) {
  try {
    await ElMessageBox.confirm(
      `确定注销用户「${row.username}」？该操作不可恢复，用户数据将被清除。`,
      '注销确认',
      { type: 'warning', confirmButtonText: '确认注销', cancelButtonText: '取消' }
    )
  } catch { return }
  try {
    await adminDeleteUser(row.id)
    ElMessage.success('用户已注销')
    users.value = users.value.filter((u) => u.id !== row.id)
  } catch {
    ElMessage.error('注销失败')
  }
}

async function approveCourseAction(row: AdminCourseApproval) {
  try {
    await approveCourse(row.id)
    ElMessage.success('已通过审核')
    pendingCourses.value = pendingCourses.value.filter((c) => c.id !== row.id)
    stats.value.pending_courses = Math.max(0, stats.value.pending_courses - 1)
  } catch {
    ElMessage.error('操作失败')
  }
}

async function rejectCourseAction(row: AdminCourseApproval) {
  try {
    await rejectCourse(row.id)
    ElMessage.success('已驳回')
    pendingCourses.value = pendingCourses.value.filter((c) => c.id !== row.id)
    stats.value.pending_courses = Math.max(0, stats.value.pending_courses - 1)
  } catch {
    ElMessage.error('操作失败')
  }
}

async function approveSeckillAction(row: AdminSeckillApproval) {
  try {
    await approveSeckill(row.id)
    ElMessage.success('审批通过')
    pendingSeckills.value = pendingSeckills.value.filter((s) => s.id !== row.id)
    stats.value.pending_seckills = Math.max(0, stats.value.pending_seckills - 1)
  } catch {
    ElMessage.error('操作失败')
  }
}

async function loadPendingTeachers() {
  loadingTeachers.value = true
  try {
    const res = await listPendingTeachers({ page: 1, page_size: 50 })
    pendingTeachers.value = res.items
  } catch {
    pendingTeachers.value = []
  } finally {
    loadingTeachers.value = false
  }
}

async function approveTeacherAction(row: AdminTeacherApproval) {
  try {
    await approveTeacher(row.id)
    ElMessage.success('讲师已通过审核')
    pendingTeachers.value = pendingTeachers.value.filter((t) => t.id !== row.id)
    stats.value.pending_teachers = Math.max(0, stats.value.pending_teachers - 1)
  } catch {
    ElMessage.error('操作失败')
  }
}

async function rejectTeacherAction(row: AdminTeacherApproval) {
  try {
    await rejectTeacher(row.id)
    ElMessage.success('讲师已拒绝')
    pendingTeachers.value = pendingTeachers.value.filter((t) => t.id !== row.id)
    stats.value.pending_teachers = Math.max(0, stats.value.pending_teachers - 1)
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadDashboard()
  loadUsers()
  loadPendingCourses()
  loadPendingSeckills()
  loadPendingTeachers()
})

watch(tab, (v) => {
  if (v === 'all-courses') loadAllCourses()
  if (v === 'reviews') loadAllReviews()
})
</script>

<style scoped>
.admin-dashboard {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 32px var(--gutter);
}

/* ===== Header ===== */
.admin-header {
  position: relative;
  border-radius: var(--radius-xl);
  overflow: hidden;
  margin-bottom: 28px;
  padding: 36px 40px;
  background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #1565c0 100%);
  color: #fff;
}
.admin-header-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 80%, rgba(101, 84, 192, 0.4) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(0, 82, 204, 0.3) 0%, transparent 50%);
  pointer-events: none;
}
.admin-header-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.admin-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.admin-icon {
  font-size: 40px;
  color: rgba(255,255,255,0.9);
  background: rgba(255,255,255,0.1);
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.admin-icon .material-symbols-outlined {
  font-size: 32px;
  color: #fff;
}
.admin-title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.01em;
}
.admin-subtitle {
  margin: 4px 0 0;
  font-size: 14px;
  color: rgba(255,255,255,0.7);
}

/* ===== Stats Cards ===== */
.admin-stats {
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
.stat-blue .stat-icon-wrap { background: linear-gradient(135deg, #1565c0, #1976d2); }
.stat-purple .stat-icon-wrap { background: linear-gradient(135deg, #6a1b9a, #8e24aa); }
.stat-orange .stat-icon-wrap { background: linear-gradient(135deg, #e65100, #f57c00); }
.stat-red .stat-icon-wrap { background: linear-gradient(135deg, #c62828, #e53935); }

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
.admin-panel {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-xl);
  box-shadow: var(--elev-1);
  overflow: hidden;
}
.admin-tabs :deep(.el-tabs__header) {
  margin: 0;
  background: var(--surface-container-low);
  border-bottom: 1px solid var(--outline-variant);
  padding: 0 16px;
}
.admin-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  height: 52px;
  line-height: 52px;
}
.admin-tabs :deep(.el-tabs__active-bar) {
  background: var(--primary);
  height: 3px;
  bottom: 0;
}
.admin-tabs :deep(.el-tabs__content) {
  padding: 24px;
}

	.tab-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.styled-table {
  margin-top: 8px;
}

/* ===== Detail Dialogs ===== */
.detail-section {
  max-height: 60vh;
  overflow-y: auto;
}
.detail-avatar {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}
.detail-avatar img {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--outline-variant);
}
.detail-cover {
  margin-bottom: 16px;
  border-radius: var(--radius);
  overflow: hidden;
}
.detail-cover img {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
}
.detail-subtitle {
  margin: 16px 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--on-surface);
  padding-bottom: 6px;
  border-bottom: 1px solid var(--outline-variant);
}
.detail-text {
  font-size: 14px;
  color: var(--on-surface-variant);
  line-height: 1.6;
  margin: 8px 0;
}
.detail-chapters {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.detail-chapter {
  background: var(--surface-container-high);
  border-radius: var(--radius);
  padding: 10px 12px;
}
.detail-chapter-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--on-surface);
  margin-bottom: 4px;
}
.detail-lessons {
  margin-top: 4px;
  padding-left: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.detail-lesson {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--on-surface);
}
.detail-lesson-duration {
  font-size: 12px;
  color: var(--on-surface-variant);
  margin-left: auto;
}
.detail-empty {
  font-size: 13px;
  color: var(--on-surface-variant);
  padding: 8px 0;
  text-align: center;
}
.detail-knowledge-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.detail-knowledge-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  padding: 4px 10px;
  background: var(--surface-container-high);
  border-radius: var(--radius);
}
.detail-price-compare {
  margin-top: 16px;
  padding: 12px;
  background: linear-gradient(135deg, #fff3e0, #ffe0b2);
  border-radius: var(--radius);
  text-align: center;
  font-size: 16px;
  font-weight: 600;
}
.compare-original {
  color: var(--on-surface-variant);
  text-decoration: line-through;
}
.compare-arrow {
  margin: 0 12px;
  color: var(--primary);
}
.compare-seckill {
  color: #e53935;
  font-size: 18px;
}
.compare-discount {
  color: #e53935;
  font-size: 14px;
}

@media (max-width: 960px) {
  .admin-stats { grid-template-columns: repeat(2, 1fr); }
  .admin-header { padding: 24px 20px; }
  .admin-header-content { flex-direction: column; align-items: flex-start; gap: 12px; }
}
@media (max-width: 600px) {
  .admin-stats { grid-template-columns: 1fr; }
}
</style>
