import { request } from './request'
import type { Course } from './courses'

export interface TeacherCourse extends Course {}

export interface SalesStatistics {
  total_sales: string
  order_count: number
  hot_courses: Array<{ id: number; title: string; sold: number }>
}

export interface TeacherSku {
  id: number
  sku_name: string
  price: string
  stock: number
  course_id: number
  course_title: string
}

export interface TeacherSeckill {
  id: number
  sku_id: number
  course_title: string
  seckill_price: string
  stock: number
  start_time: string
  end_time: string
  status: string
  created_at: string
}

export function listTeacherCourses(params: Record<string, unknown>) {
  return request.get<unknown, { total: number; items: TeacherCourse[] }>('/teacher/courses', { params })
}

export function getTeacherSales() {
  return request.get<unknown, SalesStatistics>('/teacher/statistics/sales')
}

export function createCourse(data: Record<string, unknown>) {
  return request.post<unknown, TeacherCourse>('/teacher/courses', data)
}

export function updateCourse(courseId: number, data: Record<string, unknown>) {
  return request.put(`/teacher/courses/${courseId}`, data)
}

export function submitCourse(courseId: number) {
  return request.patch(`/teacher/courses/${courseId}/submit`)
}

export function closeCourse(courseId: number) {
  return request.patch(`/teacher/courses/${courseId}/close`)
}

export function listTeacherSkus() {
  return request.get<unknown, TeacherSku[]>('/teacher/skus')
}

export function createTeacherSeckill(data: {
  sku_id: number
  seckill_price: number
  stock: number
  limit_quantity: number
  start_time: string
  end_time: string
}) {
  return request.post('/teacher/seckills', data)
}

export function listTeacherSeckills(params?: { page?: number; page_size?: number }) {
  return request.get<unknown, { total: number; items: TeacherSeckill[] }>('/teacher/seckills', { params })
}

/* ── Chapter & Lesson Management ── */

export interface ChapterItem {
  id: number
  title: string
  sort_order: number
  lessons: LessonItem[]
}

export interface LessonItem {
  id: number
  title: string
  video_url?: string | null
  duration: number
  sort_order: number
}

export interface LessonKnowledgeItem {
  id: number
  file_name: string
  file_url: string
  file_type: string
  file_size: number
  created_at: string
}

export function getTeacherChapters(courseId: number) {
  return request.get<unknown, ChapterItem[]>(`/teacher/courses/${courseId}/chapters`)
}

export function createChapter(courseId: number, data: { title: string }) {
  return request.post<unknown, ChapterItem>(`/teacher/courses/${courseId}/chapters`, data)
}

export function updateChapter(chapterId: number, data: { title?: string; sort_order?: number }) {
  return request.put<unknown, ChapterItem>(`/teacher/chapters/${chapterId}`, data)
}

export function deleteChapter(chapterId: number) {
  return request.delete(`/teacher/chapters/${chapterId}`)
}

export function createLesson(chapterId: number, data: { title: string; video_url?: string | null; duration?: number; sort_order?: number }) {
  return request.post<unknown, LessonItem>(`/teacher/chapters/${chapterId}/lessons`, data)
}

export function updateLesson(lessonId: number, data: { title?: string; video_url?: string | null; duration?: number; sort_order?: number }) {
  return request.put<unknown, LessonItem>(`/teacher/lessons/${lessonId}`, data)
}

export function deleteLesson(lessonId: number) {
  return request.delete(`/teacher/lessons/${lessonId}`)
}

/* ── Course Knowledge Base ── */

export interface CourseKnowledgeItem {
  id: number
  course_id: number
  file_name: string
  file_url: string
  file_type: string
  file_size: number
  created_at: string
}

export function getCourseKnowledge(courseId: number) {
  return request.get<unknown, CourseKnowledgeItem[]>(`/teacher/courses/${courseId}/knowledge`)
}

export function uploadCourseKnowledge(courseId: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post<unknown, CourseKnowledgeItem>(`/teacher/courses/${courseId}/knowledge`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

export function deleteCourseKnowledge(courseId: number, knowledgeId: number) {
  return request.delete(`/teacher/courses/${courseId}/knowledge/${knowledgeId}`)
}

/* ── Lesson Knowledge Base ── */

export function getLessonKnowledge(lessonId: number) {
  return request.get<unknown, LessonKnowledgeItem[]>(`/teacher/lessons/${lessonId}/knowledge`)
}

export function uploadLessonKnowledge(lessonId: number, file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post<unknown, LessonKnowledgeItem>(`/teacher/lessons/${lessonId}/knowledge`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

export function deleteLessonKnowledge(lessonId: number, knowledgeId: number) {
  return request.delete(`/teacher/lessons/${lessonId}/knowledge/${knowledgeId}`)
}
