import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getMe, login, loginByPhone, logoutApi, register, type RegisterPayload, type UserInfo, type UserRole } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('knowai_token') || '')
  const user = ref<UserInfo | null>(null)
  const isLoggedIn = computed(() => Boolean(token.value))
  const role = computed<UserRole | undefined>(() => user.value?.role)

  async function loginByPassword(account: string, password: string) {
    const result = await login({ account, password })
    token.value = result.access_token
    localStorage.setItem('knowai_token', token.value)
    await fetchMe()
  }

  async function loginByPhoneCode(phone: string, code: string) {
    const result = await loginByPhone({ phone, code })
    token.value = result.access_token
    localStorage.setItem('knowai_token', token.value)
    await fetchMe()
  }

  async function registerAccount(payload: RegisterPayload) {
    await register(payload)
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      // Short timeout so a dead backend doesn't freeze route navigation
      user.value = await getMe()
    } catch (err: unknown) {
      // 401 → token invalid/expired, clear it so user re-logs in
      // Other errors (network/5xx) → keep token, just leave user=null; the next
      // successful fetchMe will populate it. This avoids logging users out on transient blips.
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 401) {
        token.value = ''
        localStorage.removeItem('knowai_token')
      }
      user.value = null
    }
  }

  async function logout() {
    if (token.value) {
      try {
        await logoutApi()
      } catch {
      }
    }
    token.value = ''
    user.value = null
    localStorage.removeItem('knowai_token')
    // Clear favorites cache so a different account logging in next doesn't see stale state.
    const { useFavoritesStore } = await import('@/stores/favorites')
    useFavoritesStore().clear()
  }

  return { token, user, isLoggedIn, role, loginByPassword, loginByPhoneCode, registerAccount, fetchMe, logout }
})
