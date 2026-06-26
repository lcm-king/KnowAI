import { request } from './request'

export function toggleFavorite(courseId: number) {
  return request.post<unknown, { favorited: boolean; message: string }>(`/favorites/${courseId}`)
}

export function checkFavorite(courseId: number) {
  return request.get<unknown, { favorited: boolean }>(`/favorites/check/${courseId}`)
}

export function listFavorites(params?: Record<string, unknown>) {
  return request.get<unknown, { total: number; items: Array<{
    id: number
    title: string
    description?: string | null
    cover?: string | null
    category?: string | null
    total_hours: number
    learn_count: number
    rating: number
  }> }>('/favorites', { params })
}
