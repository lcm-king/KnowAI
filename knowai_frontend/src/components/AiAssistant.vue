<template>
  <Teleport to="body">
    <div v-if="visible" class="ai-assistant-overlay" @click.self="close" />
    <Transition name="slide-up">
      <div v-if="visible" class="ai-assistant-panel">
        <!-- Header -->
        <div class="panel-header">
          <div class="header-left">
            <div class="ai-avatar">
              <span class="material-symbols-outlined">smart_toy</span>
            </div>
            <div>
              <p class="header-title">学伴助手</p>
              <p class="header-status">在线</p>
            </div>
          </div>
          <div class="header-actions">
            <button class="icon-btn" title="历史记录" @click="showSessions = !showSessions">
              <span class="material-symbols-outlined">history</span>
            </button>
            <button class="icon-btn" title="新建会话" @click="newSession">
              <span class="material-symbols-outlined">add_circle</span>
            </button>
            <button class="close-btn" @click="close">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
        </div>

        <!-- Session list panel -->
        <Transition name="slide-right">
          <div v-if="showSessions" class="session-panel">
            <div class="session-panel-header">
              <span class="material-symbols-outlined">history</span>
              <span>历史记录</span>
              <button class="icon-btn" @click="showSessions = false">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>
            <div class="session-list">
              <div
                v-for="s in sessions"
                :key="s.session_id"
                :class="['session-item', { active: s.session_id === sessionId }]"
                @click="switchSession(s.session_id)"
              >
                <div class="session-item-main">
                  <span class="material-symbols-outlined session-icon">chat</span>
                  <div>
                    <p class="session-title">{{ s.title }}</p>
                    <p class="session-meta">{{ s.message_count }} 条消息 · {{ formatTime(s.updated_at) }}</p>
                  </div>
                </div>
                <button class="session-del" @click.stop="deleteSession(s.session_id)" title="删除">
                  <span class="material-symbols-outlined">delete</span>
                </button>
              </div>
              <div v-if="!sessions.length" class="session-empty">
                <span class="material-symbols-outlined">forum</span>
                <p>暂无历史记录</p>
              </div>
            </div>
          </div>
        </Transition>

        <!-- Messages -->
        <div ref="msgContainer" class="messages">
          <div v-for="(item, index) in messages" :key="index" :class="['msg', item.role]">
            <div class="msg-content">{{ item.content }}</div>
          </div>
          <div v-if="loading" class="msg assistant">
            <div class="msg-content typing">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
        </div>

        <!-- Input -->
        <div class="panel-input">
          <input
            v-model="text"
            class="input-field"
            placeholder="问问课程、学习计划或作业问题..."
            :disabled="loading"
            @keyup.enter="send"
          />
          <button class="send-btn" @click="send" :disabled="!text.trim() || loading">
            <span class="material-symbols-outlined">{{ loading ? 'hourglass_top' : 'send' }}</span>
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
  <button class="ai-fab" @click="visible = true">
    <span class="fab-pulse" aria-hidden="true" />
    <span class="fab-inner">
      <span class="material-symbols-outlined">auto_awesome</span>
    </span>
  </button>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { chat, getChatHistory, getChatSessions, deleteChatSession, type ChatSession } from '@/api/ai'

const SESSION_KEY = 'ai_assistant_session'

const visible = ref(false)
const text = ref('')
const msgContainer = ref<HTMLDivElement>()
const loading = ref(false)
const messages = ref<{ role: string; content: string }[]>([])
const sessionId = ref('')
const showSessions = ref(false)
const sessions = ref<ChatSession[]>([])

onMounted(() => {
  const stored = localStorage.getItem(SESSION_KEY)
  if (stored) {
    sessionId.value = stored
  } else {
    sessionId.value = crypto.randomUUID()
    localStorage.setItem(SESSION_KEY, sessionId.value)
  }
})

watch(visible, async (v) => {
  if (v) {
    await loadSessions()
    await loadHistory()
    await nextTick()
  }
  scrollBottom()
})

function close() {
  visible.value = false
  showSessions.value = false
}

function formatTime(t: string) {
  const d = new Date(t)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 86400000) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function newSession() {
  sessionId.value = crypto.randomUUID()
  localStorage.setItem(SESSION_KEY, sessionId.value)
  messages.value = [{ role: 'assistant', content: '你好，我是学伴学习助手。有什么可以帮助你的？' }]
  showSessions.value = false
}

async function switchSession(id: string) {
  sessionId.value = id
  localStorage.setItem(SESSION_KEY, id)
  showSessions.value = false
  await loadHistory()
  await nextTick()
  scrollBottom()
}

async function loadSessions() {
  try {
    const res = await getChatSessions()
    sessions.value = res.sessions || []
  } catch {
    // ignore
  }
}

async function loadHistory() {
  if (!sessionId.value) return
  try {
    const res = await getChatHistory(sessionId.value)
    if (res.messages && res.messages.length > 0) {
      messages.value = res.messages
      return
    }
  } catch {
    // history unavailable — start fresh
  }
  if (messages.value.length === 0) {
    messages.value = [{ role: 'assistant', content: '你好，我是学伴学习助手。有什么可以帮助你的？' }]
  }
}

async function deleteSession(id: string) {
  try {
    await deleteChatSession(id)
    sessions.value = sessions.value.filter(s => s.session_id !== id)
    if (id === sessionId.value) newSession()
  } catch {
    // ignore
  }
}

async function scrollBottom() {
  await nextTick()
  if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight
}

async function send() {
  const content = text.value.trim()
  if (!content || loading.value) return
  loading.value = true
  messages.value.push({ role: 'user', content })
  text.value = ''
  await scrollBottom()
  try {
    const result = await chat(content, sessionId.value)
    messages.value.push({ role: 'assistant', content: result.answer })
    await loadSessions() // refresh session list
  } catch {
    messages.value.push({ role: 'assistant', content: '当前聊天接口未启用，可先使用智能出题和 AI 批改功能。' })
  } finally {
    loading.value = false
    await scrollBottom()
  }
}
</script>

<style scoped>
.ai-fab {
  position: fixed;
  right: 28px;
  bottom: 32px;
  z-index: 40;
  width: 60px;
  height: 60px;
  border-radius: 20px;
  background: var(--ai-gradient);
  border: none;
  color: #fff;
  cursor: pointer;
  box-shadow: var(--shadow-glow-ai);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
}
.ai-fab:hover { transform: scale(1.08); box-shadow: 0 16px 40px rgba(101, 84, 192, 0.45); }
.ai-fab .material-symbols-outlined { font-size: 28px; }
.fab-pulse {
  position: absolute;
  inset: 0;
  border-radius: 20px;
  background: var(--ai-gradient);
  opacity: 0.6;
  animation: fab-pulse 2.5s ease-out infinite;
  pointer-events: none;
}
@keyframes fab-pulse {
  0% { transform: scale(1); opacity: 0.6; }
  100% { transform: scale(1.6); opacity: 0; }
}
.fab-inner { position: relative; z-index: 1; display: flex; align-items: center; justify-content: center; }

.ai-assistant-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.25);
}

.ai-assistant-panel {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 101;
  width: 380px;
  height: 560px;
  border-radius: var(--radius-xl);
  background: var(--surface-container-lowest);
  box-shadow: var(--elev-3);
  border: 1px solid var(--outline-variant);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid var(--outline-variant);
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-actions { display: flex; align-items: center; gap: 4px; }
.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: var(--on-surface-variant);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.icon-btn:hover { background: var(--surface-container-low); color: var(--primary); }
.icon-btn .material-symbols-outlined { font-size: 20px; }
.header-left { display: flex; align-items: center; gap: 12px; }
.ai-avatar {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: var(--ai-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.ai-avatar .material-symbols-outlined { font-size: 22px; }
.header-title { margin: 0; font-size: 15px; font-weight: 600; color: var(--on-surface); }
.header-status { margin: 0; font-size: 12px; color: var(--tertiary); }
.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: var(--on-surface-variant);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.close-btn:hover { background: var(--surface-container-low); }
.close-btn .material-symbols-outlined { font-size: 20px; }

/* Session panel */
.session-panel {
  position: absolute;
  inset: 0;
  z-index: 10;
  background: var(--surface-container-lowest);
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-xl);
}
.session-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--outline-variant);
  font-size: 15px;
  font-weight: 600;
  color: var(--on-surface);
}
.session-panel-header .icon-btn { margin-left: auto; }
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 4px;
}
.session-item:hover { background: var(--surface-container-low); }
.session-item.active { background: var(--primary-container); }
.session-item-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}
.session-icon {
  font-size: 20px;
  color: var(--on-surface-variant);
  flex-shrink: 0;
}
.session-title {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--on-surface);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-meta {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--outline);
}
.session-del {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: transparent;
  border: none;
  color: var(--outline);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  opacity: 0;
  transition: all 0.2s;
}
.session-item:hover .session-del { opacity: 1; }
.session-del:hover { color: var(--error); background: var(--error-container); }
.session-del .material-symbols-outlined { font-size: 18px; }
.session-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--outline);
}
.session-empty .material-symbols-outlined { font-size: 40px; }
.session-empty p { margin: 0; font-size: 13px; }

.slide-right-enter-active,
.slide-right-leave-active { transition: all 0.22s ease; }
.slide-right-enter-from,
.slide-right-leave-to { transform: translateX(30px); opacity: 0; }

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.msg { display: flex; }
.msg.user { justify-content: flex-end; }
.msg-content {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--on-surface);
}
.msg.assistant .msg-content {
  background: var(--surface-container-low);
  border-bottom-left-radius: 4px;
}
.msg.user .msg-content {
  background: var(--ai-gradient-soft);
  border-bottom-right-radius: 4px;
  color: var(--on-surface);
}

.msg-content.typing {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 14px 18px;
}
.msg-content.typing .dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--on-surface-variant);
  animation: typing-bounce 1.2s infinite ease-in-out;
}
.msg-content.typing .dot:nth-child(2) { animation-delay: 0.15s; }
.msg-content.typing .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

.panel-input {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px 16px;
  border-top: 1px solid var(--outline-variant);
}
.input-field {
  flex: 1;
  height: 44px;
  padding: 0 16px;
  border-radius: 12px;
  border: 1px solid var(--outline-variant);
  background: var(--surface-container-low);
  font-size: 14px;
  font-family: inherit;
  color: var(--on-surface);
  outline: none;
  transition: border 0.2s;
}
.input-field:focus { border-color: var(--primary); background: var(--surface-container-lowest); }
.input-field::placeholder { color: var(--outline); }
.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--ai-gradient);
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s;
}
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.send-btn .material-symbols-outlined { font-size: 22px; }

.slide-up-enter-active,
.slide-up-leave-active { transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-up-enter-from,
.slide-up-leave-to { opacity: 0; transform: translateY(20px) scale(0.96); transform-origin: bottom right; }

@media (max-width: 480px) {
  .ai-assistant-panel { right: 12px; bottom: 12px; width: calc(100vw - 24px); height: 500px; }
  .ai-fab { right: 16px; bottom: 20px; width: 52px; height: 52px; border-radius: 16px; }
}
</style>