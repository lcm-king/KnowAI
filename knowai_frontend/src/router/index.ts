import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  { path: '/', component: () => import('@/layouts/MainLayout.vue'), children: [
    { path: '', name: 'home', component: () => import('@/views/HomePage.vue') },
    { path: 'courses', name: 'courses', component: () => import('@/views/CourseList.vue') },
    { path: 'courses/:id', name: 'course-detail', component: () => import('@/views/CourseDetail.vue') },
    { path: 'cart', name: 'cart', component: () => import('@/views/Cart.vue'), meta: { requiresAuth: true } },
    { path: 'orders', name: 'orders', component: () => import('@/views/OrderList.vue'), meta: { requiresAuth: true } },
    { path: 'orders/:orderSn', name: 'order-detail', component: () => import('@/views/OrderDetail.vue'), meta: { requiresAuth: true } },
    { path: 'pay/:orderSn', name: 'pay', component: () => import('@/views/PayPage.vue'), meta: { requiresAuth: true } },
    { path: 'my-courses', name: 'my-courses', component: () => import('@/views/MyCourses.vue'), meta: { requiresAuth: true } },
    { path: 'learn/:id', name: 'learn', component: () => import('@/views/CourseLearning.vue'), meta: { requiresAuth: true } },
    { path: 'profile', name: 'profile', component: () => import('@/views/Profile.vue'), meta: { requiresAuth: true } },
    { path: 'homework', name: 'homework', component: () => import('@/views/HomeworkPage.vue'), meta: { requiresAuth: true } },
    { path: 'ai-recommend', name: 'ai-recommend', component: () => import('@/views/AICourseRecommend.vue'), meta: { requiresAuth: true } },
    { path: 'teacher', name: 'teacher', component: () => import('@/views/TeacherDashboard.vue'), meta: { requiresAuth: true, roles: ['teacher'] } },
    { path: 'admin', name: 'admin', component: () => import('@/views/AdminDashboard.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
  ] },
  { path: '/login', name: 'login', component: () => import('@/views/LoginPage.vue') },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFound.vue') },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  // Try to restore session if token exists but user data not loaded yet
  if (userStore.token && !userStore.user) {
    await userStore.fetchMe()
    // If fetchMe still couldn't get user data, try again once (transient error)
    if (userStore.token && !userStore.user) {
      await userStore.fetchMe()
    }
    // If still no user after retry, clear stale session
    if (userStore.token && !userStore.user) {
      await userStore.logout()
    }
  }

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  const roles = to.meta.roles as string[] | undefined
  if (roles?.length && (!userStore.role || !roles.includes(userStore.role))) {
    ElMessage.error('无权访问该页面')
    return { name: 'home' }
  }

  return true
})
