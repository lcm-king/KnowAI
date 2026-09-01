import { request } from './request'

export interface Course {
  id: number
  teacher_id: number
  title: string
  description?: string | null
  cover?: string | null
  video_url?: string | null
  category?: string | null
  total_hours: number
  learn_count: number
  rating: number
  status: string
  skus?: CourseSku[]
  seckill_activity_id?: number | null
  seckill_price?: string | null
  seckill_end_time?: string | null
  /** Real-time remaining stock for the seckill activity. null/undefined when
   * no active seckill. For seckill, 0 means sold out (NOT unlimited). */
  seckill_stock?: number | null
  price?: string | null
  stock?: number | null
  validity_days?: number | null
  is_purchased?: boolean
}

export interface CourseSku {
  id: number
  course_id: number
  sku_name?: string | null
  price: string
  stock: number
  validity_days: number
  status: string
}

export function listCourses(params: Record<string, unknown>) {
  return request.get<unknown, { total: number; items: Course[] }>('/courses', { params })
}

export function getCourse(courseId: number) {
  return request.get<unknown, Course>(`/courses/${courseId}`)
}

export function getCourseSkus(courseId: number) {
  return request.get<unknown, CourseSku[]>(`/courses/${courseId}/skus`)
}

export interface MyLearningCourse {
  id: number
  title: string
  cover?: string | null
  category?: string | null
  total_hours: number
  learn_count: number
  rating: number
  sku_id: number
  sku_name?: string | null
  expire_date: string | null
  progress: number
  is_trial?: boolean
}

export function listMyLearning() {
  return request.get<unknown, { total: number; items: MyLearningCourse[] }>('/courses/my-learning')
}

export interface LessonData {
  id: number
  title: string
  video_url?: string | null
  duration: number
  sort_order: number
  is_locked: boolean
}

export interface ChapterData {
  id: number
  title: string
  sort_order: number
  lessons: LessonData[]
}

export function getCourseChapters(courseId: number) {
  return request.get<unknown, ChapterData[]>(`/courses/${courseId}/chapters`)
}

export function updateLessonProgress(courseId: number, lessonId: number, position: number, duration?: number) {
  return request.post(`/courses/${courseId}/progress`, { lesson_id: lessonId, position, duration })
}

export function getCourseProgress(courseId: number) {
  return request.get<unknown, { learned_lessons: number; progress: number; last_lesson_id: number | null; last_position: number }>(`/courses/${courseId}/progress`)
}

export function searchCourses(params: Record<string, unknown>) {
  return request.get<unknown, { total: number; page: number; size: number; items: Array<{ course_id: number; title: string; cover?: string | null; price: number; teacher_name: string; sales: number; highlight?: string[] }> }>('/search/courses', { params })
}

export function listSeckillCourses() {
  return request.get<unknown, Course[]>('/courses/seckill')
}
