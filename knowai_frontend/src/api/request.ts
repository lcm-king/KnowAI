import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useLoadingStore } from '@/stores/loading'
import { useUserStore } from '@/stores/user'

export const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 120000,
})

request.interceptors.request.use((config) => {
  const loadingStore = useLoadingStore()
  const userStore = useUserStore()
  loadingStore.start()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

let redirecting = false

request.interceptors.response.use(
  (response) => {
    useLoadingStore().finish()
    return response.data
  },
  async (error) => {
    useLoadingStore().finish()
    const status = error.response?.status
    let detail = error.response?.data?.detail
    // FastAPI 422 validation errors return detail as an array
    if (Array.isArray(detail)) {
      detail = detail.map((d: { msg?: string }) => d.msg || '').filter(Boolean).join('；')
    }
    const url: string | undefined = error.config?.url
    const isAuthMe = url?.includes('/auth/me')

    if (status === 401) {
      if (url?.includes('/auth/login')) {
        ElMessage.error(detail || '账号或密码错误')
      } else if (!isAuthMe) {
        // Only show "session expired" for actual user-initiated requests, not background auth checks
        const userStore = useUserStore()
        await userStore.logout()
        ElMessage.warning(detail || '登录已过期，请重新登录')
        if (!redirecting && !window.location.pathname.startsWith('/login')) {
          redirecting = true
          const redirect = window.location.pathname + window.location.search
          window.location.href = `/login?redirect=${encodeURIComponent(redirect)}`
        }
      } else {
        // Silently handle 401 from /auth/me - fetchMe() manages this internally
        const userStore = useUserStore()
        await userStore.logout()
      }
    } else if (status === 403) {
      ElMessage.error(detail || '权限不足')
    } else if (status === 429) {
      ElMessage.warning(detail || '操作过于频繁，请稍后再试')
    } else if (!isAuthMe) {
      // Only show generic errors for non-auth-me requests
      ElMessage.error(detail || error.message || '请求失败')
    }

    return Promise.reject(error)
  },
)

