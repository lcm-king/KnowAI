import { request } from './request'

export interface Review {
  id: number
  course_id: number
  user_id: number
  username: string | null
  rating: number
  content: string | null
  created_at: string
  updated_at: string | null
}

export interface ReviewListResponse {
  total: number
  items: Review[]
  average_rating: number
  review_count: number
}

export function listCourseReviews(courseId: number, params?: Record<string, unknown>) {
  return request.get<unknown, ReviewListResponse>(`/courses/${courseId}/reviews`, { params })
}

export function createCourseReview(courseId: number, data: { rating: number; content?: string | null }) {
  return request.post<unknown, Review>(`/courses/${courseId}/reviews`, data)
}

export function updateCourseReview(courseId: number, reviewId: number, data: { rating?: number; content?: string | null }) {
  return request.put<unknown, Review>(`/courses/${courseId}/reviews/${reviewId}`, data)
}

export function deleteCourseReview(courseId: number, reviewId: number) {
  return request.delete(`/courses/${courseId}/reviews/${reviewId}`)
}
