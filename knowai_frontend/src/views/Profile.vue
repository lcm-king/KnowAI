<template>
  <div class="container">
    <h1 class="page-title">个人中心</h1>

    <!-- User Info -->
    <div class="panel">
      <p>用户名：{{ userStore.user?.username }}</p>
      <p>手机号：{{ userStore.user?.phone }}</p>
      <p>邮箱：{{ userStore.user?.email }}</p>
      <p>角色：{{ roleLabel(userStore.user?.role) }}</p>
    </div>

    <!-- Teacher Application -->
    <div v-if="userStore.user?.role === 'student'" class="panel">
      <h3>成为讲师</h3>
      <p class="teacher-desc">申请成为讲师后，你可以创建和发布课程内容。需要管理员审核通过。</p>
      <template v-if="!teacherApplied">
        <el-input v-model="teacherName" placeholder="讲师姓名" size="large" style="margin-bottom:12px" />
        <el-input v-model="teacherBio" placeholder="个人简介（选填）" type="textarea" :rows="3" size="large" style="margin-bottom:16px" />
        <button class="btn-ai" :loading="applyingTeacher" @click="handleApplyTeacher">
          <span class="material-symbols-outlined">school</span> 提交申请
        </button>
      </template>
      <p v-else class="teacher-pending"><span class="material-symbols-outlined">hourglass_top</span> 讲师申请已提交，等待管理员审核</p>
    </div>

    <!-- Favorites -->
    <div class="panel">
      <h3>收藏夹</h3>
      <div v-if="loading" class="fav-loading">
        <span class="material-symbols-outlined cd-spin">progress_activity</span>
        <p>加载中...</p>
      </div>
      <div v-else-if="favorites.length === 0" class="fav-empty">
        <span class="material-symbols-outlined">bookmark_border</span>
        <p>还没有收藏任何课程</p>
        <RouterLink to="/courses" class="btn-ai">去逛逛</RouterLink>
      </div>
      <div v-else class="fav-grid">
        <div v-for="course in favorites" :key="course.id" class="fav-card">
          <RouterLink :to="`/courses/${course.id}`">
            <el-image :src="course.cover || ''" fit="cover" class="fav-cover">
              <template #error>
                <div class="cover-fallback">
                  <span class="material-symbols-outlined">bookmark</span>
                </div>
              </template>
            </el-image>
          </RouterLink>
          <div class="fav-info">
            <RouterLink :to="`/courses/${course.id}`" class="fav-title">{{ course.title }}</RouterLink>
            <span class="fav-category">{{ course.category || '综合' }}</span>
          </div>
          <button class="fav-unbtn" @click.stop="handleUnfavorite(course.id)">
            <span class="material-symbols-outlined">bookmark</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Account deletion -->
    <div class="panel danger-panel">
      <h3>注销账号</h3>
      <p class="danger-desc">注销后账号将无法登录，个人信息将被清除，订单与收藏记录将被移除。此操作不可恢复。</p>
      <button class="btn-danger" @click="showDeleteDialog = true">
        <span class="material-symbols-outlined">person_remove</span>
        注销我的账号
      </button>
    </div>

    <!-- Delete account confirmation dialog -->
    <el-dialog v-model="showDeleteDialog" title="确认注销账号" width="420px" center>
      <div class="del-dialog-body">
        <div class="del-warning-icon">
          <span class="material-symbols-outlined">warning</span>
        </div>
        <p class="del-warning-text">您正在申请注销账号，此操作<b>不可恢复</b>。</p>
        <ul class="del-effects">
          <li>账号将被禁用，无法再登录</li>
          <li>用户名、邮箱、手机号将被清除</li>
          <li>收藏夹将被清空</li>
          <li>历史订单记录将保留但与您脱离关联</li>
        </ul>
        <p class="del-confirm-label">请输入登录密码以确认：</p>
        <el-input
          v-model="deletePassword"
          type="password"
          placeholder="登录密码"
          show-password
          size="large"
        />
      </div>
      <template #footer>
        <el-button @click="showDeleteDialog = false">取消</el-button>
        <el-button type="danger" :loading="deleting" @click="confirmDelete">
          确认注销
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listFavorites, toggleFavorite } from '@/api/favorites'
import { applyTeacher, deleteAccountApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()

const roleLabels: Record<string, string> = { admin: '管理员', teacher: '讲师', student: '学生' }
function roleLabel(role?: string) { return role ? (roleLabels[role] || role) : '' }

const favorites = ref<any[]>([])
const loading = ref(false)

const teacherName = ref('')
const teacherBio = ref('')
const applyingTeacher = ref(false)
const teacherApplied = ref(!!(userStore.user?.teacher_id))

const showDeleteDialog = ref(false)
const deletePassword = ref('')
const deleting = ref(false)

async function handleApplyTeacher() {
  if (!teacherName.value.trim()) {
    ElMessage.warning('请输入讲师姓名')
    return
  }
  applyingTeacher.value = true
  try {
    await applyTeacher({ name: teacherName.value.trim(), bio: teacherBio.value.trim() || undefined })
    ElMessage.success('讲师申请已提交，等待管理员审核')
    teacherApplied.value = true
  } catch {
    // interceptor already showed error
  } finally {
    applyingTeacher.value = false
  }
}

async function handleUnfavorite(courseId: number) {
  try {
    await toggleFavorite(courseId)
    favorites.value = favorites.value.filter((c) => c.id !== courseId)
    ElMessage.success('已取消收藏')
  } catch {
    ElMessage.error('取消收藏失败')
  }
}

async function confirmDelete() {
  if (!deletePassword.value) {
    ElMessage.warning('请输入密码')
    return
  }
  deleting.value = true
  try {
    await deleteAccountApi(deletePassword.value)
    showDeleteDialog.value = false
    await userStore.logout()
    router.push('/')
    ElMessageBox.alert('您的账号已注销，感谢您的使用。', '注销成功', {
      confirmButtonText: '返回首页',
      type: 'success',
    })
  } catch {
    // interceptor 已显示错误
  } finally {
    deleting.value = false
    deletePassword.value = ''
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const result = await listFavorites({ page: 1, page_size: 50 })
    favorites.value = result.items
  } catch {
    favorites.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.panel {
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 20px;
}
.panel h3 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 600;
}

.fav-loading, .fav-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  color: var(--on-surface-variant);
}
.fav-loading .material-symbols-outlined { font-size: 48px; color: var(--primary); }
.fav-empty .material-symbols-outlined { font-size: 56px; opacity: 0.4; }
.fav-empty p { margin: 12px 0 16px; font-size: 14px; }

.fav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.fav-card {
  background: var(--surface-container-low);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius);
  overflow: hidden;
  transition: all 0.2s;
  position: relative;
}
.fav-card:hover {
  border-color: var(--primary);
  box-shadow: var(--elev-1);
}

.fav-cover {
  width: 100%;
  height: 140px;
  display: block;
}
.fav-cover .el-image { width: 100%; height: 100%; }

.fav-info {
  padding: 12px 14px 14px;
}
.fav-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--on-surface);
  text-decoration: none;
  display: block;
  margin-bottom: 6px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fav-title:hover { color: var(--primary); }
.fav-category {
  font-size: 12px;
  color: var(--on-surface-variant);
  background: var(--surface-container-lowest);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.fav-unbtn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s;
  color: var(--warning);
}
.fav-unbtn:hover {
  background: var(--danger);
  color: #fff;
}
.fav-unbtn .material-symbols-outlined { font-size: 18px; }

.cd-spin { animation: cd-spin 1s linear infinite; }
@keyframes cd-spin { to { transform: rotate(360deg); } }

.danger-panel {
  border-color: rgba(255, 86, 48, 0.3);
}
.danger-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--on-surface-variant);
  line-height: 1.6;
}
.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: var(--radius);
  background: var(--danger);
  color: #fff;
  border: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: opacity 0.2s;
}
.btn-danger:hover { opacity: 0.9; }
.btn-danger .material-symbols-outlined { font-size: 18px; }

.del-dialog-body {
  text-align: center;
  padding: 0 8px;
}
.del-warning-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}
.del-warning-icon .material-symbols-outlined {
  font-size: 48px;
  color: var(--warning);
}
.del-warning-text {
  font-size: 15px;
  margin: 0 0 14px;
}
.del-warning-text b { color: var(--danger); }
.del-effects {
  text-align: left;
  background: var(--surface-container-low);
  border-radius: var(--radius);
  padding: 12px 16px 12px 30px;
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--on-surface-variant);
  line-height: 1.8;
}
.del-confirm-label {
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 8px;
}
.teacher-desc { font-size: 13px; color: var(--on-surface-variant); margin: 0 0 16px; line-height: 1.6; }
.teacher-pending {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px; background: rgba(101, 84, 192, 0.1);
  border-radius: var(--radius); color: var(--primary); font-size: 14px; font-weight: 600;
}
.teacher-pending .material-symbols-outlined { font-size: 20px; }
.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--primary-container), var(--secondary-container));
  min-height: 140px;
}
.cover-fallback .material-symbols-outlined {
  font-size: 40px;
  opacity: 0.5;
  color: var(--on-primary-container);
}
</style>
