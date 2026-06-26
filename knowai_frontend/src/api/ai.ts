import { request } from './request'
import type { Course } from './courses'

export interface QuizQuestion {
  question: string
  options: string[]
  answer: string
}

// ── New Knowledge-Base AI Endpoints (LangChain + LangGraph) ──

export function generateQuiz(data: {
  course_id: number
  chapter_title: string
  knowledge_points: string[]
  lesson_id?: number
  question_types?: string[]
  difficulty?: string
  count?: number
}) {
  return request.post<unknown, { questions: QuizQuestion[]; mock: boolean }>('/ai/knowledge/quiz', data)
}

export function recommendCourses(data: { description: string; goal?: string; limit?: number }) {
  return request.post<unknown, { items: Course[]; mock: boolean }>('/ai/knowledge/recommend', data)
}

export function gradeHomework(data: { question: string; student_answer: string; course_id?: number }) {
  return request.post<unknown, { score: number; comment: string; mock: boolean }>('/ai/knowledge/grade', data)
}

export function chat(message: string, sessionId?: string) {
  return request.post<unknown, { answer: string; mock?: boolean }>('/ai/knowledge/chat', { message, session_id: sessionId })
}

export function getChatHistory(sessionId: string) {
  return request.get<unknown, { messages: { role: string; content: string }[] }>('/ai/knowledge/chat/history', { params: { session_id: sessionId } })
}

export interface ChatSession {
  session_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export function getChatSessions() {
  return request.get<unknown, { sessions: ChatSession[] }>('/ai/knowledge/chat/sessions')
}

export function deleteChatSession(sessionId: string) {
  return request.delete<unknown, { message: string }>('/ai/knowledge/chat/sessions/' + sessionId)
}

// ── Old endpoints (deprecated, kept for backward compatibility) ──

export function generateQuizOld(data: { course_id: number; chapter_title: string; knowledge_points: string[] }) {
  return request.post<unknown, { questions: QuizQuestion[]; mock: boolean }>('/ai/generate_quiz', data)
}

export function recommendCoursesOld() {
  return request.post<unknown, { items: Course[]; mock: boolean }>('/ai/recommend_courses')
}

export function gradeHomeworkOld(data: { homework_id: number; student_answer: string }) {
  return request.post<unknown, { score: number; comment: string; mock: boolean }>('/ai/grade_homework', data)
}
