import { request } from './request'

export function toggleFavorite(courseId: number) {
  return request.post<unknown, { favorited: boolean; message: string }>(`/favorites/${courseId}`)
}

export function checkFavorite(courseId: number) {
  return request.get<unknown, { favorited: boolean }>(`/favorites/check/${courseId}`)
}

export function getFavoriteIds() {
  // Background pre-fetch on app load - silent so it doesn't trigger the
  // global loading bar or error toast if it fails.
  return request.get<unknown, { ids: number[] }>('/favorites/ids', { silent: true })
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
