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
      user.value = await getMe()
    } catch {
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
  }

  return { token, user, isLoggedIn, role, loginByPassword, loginByPhoneCode, registerAccount, fetchMe, logout }
})
