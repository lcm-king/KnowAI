import { request } from './request'

export type UserRole = 'student' | 'teacher' | 'admin'
export interface UserInfo {
  id: number
  username: string
  phone: string
  email: string
  role: UserRole
  teacher_id?: number | null
  is_active: boolean
}

export interface RegisterPayload {
  username: string
  phone: string
  email: string
  password: string
  code: string
}

export function sendCode(data: { target: string }) {
  return request.post<unknown, { message: string }>('/auth/send-code', data)
}

export function sendLoginCode(data: { target: string }) {
  return request.post<unknown, { message: string }>('/auth/send-login-code', data)
}

export function register(data: RegisterPayload) {
  return request.post<unknown, { message: string }>('/auth/register', data)
}

export function login(data: { account: string; password: string }) {
  return request.post<unknown, { access_token: string; token_type: string }>('/auth/login', data)
}

export function loginByPhone(data: { phone: string; code: string }) {
  return request.post<unknown, { access_token: string; token_type: string }>('/auth/login/phone', data)
}

export function applyTeacher(data: { name: string; bio?: string }) {
  return request.post<unknown, { message: string }>('/auth/apply-teacher', data)
}

export function getMe() {
  return request.get<unknown, UserInfo>('/auth/me')
}

export function logoutApi() {
  return request.post('/auth/logout')
}

export function deleteAccountApi(password: string) {
  return request.post<unknown, { message: string }>('/auth/delete-account', { password })
}
