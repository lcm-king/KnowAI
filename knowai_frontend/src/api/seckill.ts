import { request } from './request'

export interface SeckillQueueResponse {
  code: number
  msg: string
  queue_id: string
}

export interface SeckillResultResponse {
  queue_id: string
  status: 'queued' | 'success' | 'failed'
  order_sn?: string | null
  message?: string | null
}

export function submitSeckill(activityId: number) {
  return request.post<unknown, SeckillQueueResponse>(`/seckill/${activityId}`)
}

export function getSeckillResult(queueId: string) {
  return request.get<unknown, SeckillResultResponse>(`/seckill/result/${queueId}`)
}
