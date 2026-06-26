import { request } from './request'

export interface CartItem {
  sku_id: number
  course_id: number
  course_title: string
  cover?: string | null
  sku_name?: string | null
  price: string
  quantity: number
  selected: boolean
  add_time: number
}

export function getCart() {
  return request.get<unknown, { total: number; items: CartItem[] }>('/cart')
}

export function addCartItem(sku_id: number) {
  return request.post('/cart/add', { sku_id, quantity: 1 })
}

export function updateCartItem(sku_id: number, selected?: boolean) {
  return request.put('/cart/update', { sku_id, selected })
}

export function removeCartItem(sku_id: number) {
  return request.delete('/cart/remove', { data: { sku_id } })
}
