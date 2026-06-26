import { request } from './request'

export interface OrderItem {
  id: number
  sku_id: number
  quantity: number
  price: string
  course_title?: string | null
  sku_name?: string | null
}

export interface Order {
  id: number
  order_sn: string
  total_amount: string
  pay_amount: string
  status: string
  expire_time: string
  pay_time: string | null
  created_at: string
  items: OrderItem[]
}

export function createOrder(sku_ids: number[]) {
  return request.post<unknown, { order_sn: string; total_amount: string; expire_time: string; direct_granted?: boolean }>('/orders/create', { sku_ids })
}

export function listOrders(params: Record<string, unknown>) {
  return request.get<unknown, { total: number; items: Order[] }>('/orders', { params })
}

export function getOrder(orderSn: string) {
  return request.get<unknown, Order>(`/orders/${orderSn}`)
}

export function createPay(order_sn: string, pay_method: 'wechat' | 'alipay') {
  return request.post<unknown, { order_sn: string; pay_method: string; pay_url?: string; qr_code_url?: string; form?: string; mock: boolean }>('/pay/create', { order_sn, pay_method })
}
