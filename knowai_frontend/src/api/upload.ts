import { request } from './request'

export interface UploadResult {
  url: string
  filename: string
  size: number
}

export function uploadCover(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post<unknown, UploadResult>('/upload/cover', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
}

export function uploadVideo(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post<unknown, UploadResult>('/upload/video', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function uploadDocument(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request.post<unknown, UploadResult>('/upload/document', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}
