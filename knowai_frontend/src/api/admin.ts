import { request } from './request'

export interface DashboardStats {
  total_users: number
  today_registrations: number
  total_teachers: number
  pending_teachers: number
  active_courses: number
  pending_courses: number
  pending_seckills: number
}

export interface AdminUser {
  id: number
  username: string
  phone: string
  email: string
  role: 'student' | 'teacher' | 'admin'
  is_active: boolean
  created_at: string
}

export interface AdminCourseApproval {
  id: number
  title: string
  teacher_id: number
  teacher_name?: string | null
  category?: string | null
  total_hours: number
  status: string
  created_at: string
}

export interface AdminSeckillApproval {
  id: number
  sku_id: number
  seckill_price: string
  stock: number
  limit_quantity: number
  start_time: string
  end_time: string
  status: string
  created_at: string
}

export function getDashboard() {
  return request.get<unknown, DashboardStats>('/admin/dashboard')
}

export function healthCheck() {
  return request.get('/admin/health')
}

export function listAdminUsers(params: Record<string, unknown>) {
  return request.get<unknown, { total: number; items: AdminUser[] }>('/admin/users', { params })
}

export function updateUserStatus(userId: number, is_active: boolean) {
  return request.patch<unknown, AdminUser>(`/admin/users/${userId}/status`, { is_active })
}

export function listPendingCourses(params: Record<string, unknown> = {}) {
  return request.get<unknown, { total: number; items: AdminCourseApproval[] }>('/admin/courses/pending', { params })
}

export function approveCourse(courseId: number) {
  return request.post(`/admin/courses/${courseId}/approve`)
}

export function rejectCourse(courseId: number) {
  return request.post(`/admin/courses/${courseId}/reject`)
}

export function listPendingSeckills(params: Record<string, unknown> = {}) {
  return request.get<unknown, { total: number; items: AdminSeckillApproval[] }>('/admin/seckills/pending', { params })
}

export function approveSeckill(activityId: number) {
  return request.post(`/admin/seckills/${activityId}/approve`)
}

export interface AdminTeacherApproval {
  id: number
  user_id: number
  username: string
  phone: string
  email: string
  name: string
  bio?: string | null
  created_at: string
}

export function listPendingTeachers(params: Record<string, unknown> = {}) {
  return request.get<unknown, { total: number; items: AdminTeacherApproval[] }>('/admin/teachers/pending', { params })
}

export function approveTeacher(teacherId: number) {
  return request.post(`/admin/teachers/${teacherId}/approve`)
}

export function rejectTeacher(teacherId: number) {
  return request.post(`/admin/teachers/${teacherId}/reject`)
}

// ── Admin User Deletion ──

export function adminDeleteUser(userId: number) {
  return request.delete(`/admin/users/${userId}`)
}

// ── Admin Course Management ──

export interface AdminCourse {
  id: number
  teacher_id: number
  title: string
  description: string | null
  cover: string | null
  category: string | null
  total_hours: number
  learn_count: number
  rating: number
  status: string
  created_at: string
  updated_at: string | null
}

export function listAllCourses(params: Record<string, unknown> = {}) {
  return request.get<unknown, { total: number; items: AdminCourse[] }>('/admin/courses', { params })
}

export function adminCreateCourse(data: Record<string, unknown>) {
  return request.post<unknown, AdminCourse>('/admin/courses', data)
}

export function adminUpdateCourse(courseId: number, data: Record<string, unknown>) {
  return request.put<unknown, AdminCourse>(`/admin/courses/${courseId}`, data)
}

export function adminDeleteCourse(courseId: number) {
  return request.delete(`/admin/courses/${courseId}`)
}

// ── Admin Review Management ──

export interface AdminReview {
  id: number
  course_id: number
  course_title: string
  user_id: number
  username: string
  rating: number
  content: string | null
  created_at: string
}

export function listAllReviews(params: Record<string, unknown> = {}) {
  return request.get<unknown, { total: number; items: AdminReview[] }>('/admin/reviews', { params })
}

export function adminDeleteReview(reviewId: number) {
  return request.delete(`/admin/reviews/${reviewId}`)
}

export function listAllTeachers() {
  return request.get<unknown, Array<{ id: number; name: string }>>('/admin/teachers')
}

// ── Admin Detail Endpoints ──

export interface AdminTeacherDetail {
  id: number
  user_id: number
  username: string
  phone: string
  email: string
  name: string
  bio: string | null
  avatar: string | null
  status: string
  created_at: string
}

export function getTeacherDetail(teacherId: number) {
  return request.get<unknown, AdminTeacherDetail>(`/admin/teachers/${teacherId}`)
}

export interface AdminCourseDetail {
  id: number
  teacher_id: number
  teacher_name: string | null
  title: string
  description: string | null
  cover: string | null
  category: string | null
  total_hours: number
  learn_count: number
  rating: number
  status: string
  created_at: string
  skus: Array<{
    id: number
    price: string
    stock: number
    sku_name: string | null
    status: string
  }>
  chapters: Array<{
    id: number
    title: string
    sort_order: number
    lessons: Array<{
      id: number
      title: string
      video_url: string | null
      duration: number
      sort_order: number
    }>
  }>
  knowledge_files: Array<{
    id: number
    file_name: string
    file_url: string
    file_size: number
    created_at: string
  }>
}

export function getCourseDetail(courseId: number) {
  return request.get<unknown, AdminCourseDetail>(`/admin/courses/${courseId}/detail`)
}

export interface AdminSeckillDetail {
  id: number
  sku_id: number
  seckill_price: string
  stock: number
  limit_quantity: number
  start_time: string
  end_time: string
  status: string
  created_at: string
  course_id: number
  course_title: string | null
  sku_price: string
  sku_name: string | null
  sku_stock: number
}

export function getSeckillDetail(activityId: number) {
  return request.get<unknown, AdminSeckillDetail>(`/admin/seckills/${activityId}`)
}
