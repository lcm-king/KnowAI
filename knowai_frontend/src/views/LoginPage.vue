<template>
  <div class="login-wrap">
    <!-- Canvas particle background -->
    <canvas ref="canvasRef" class="particle-canvas"></canvas>

    <div class="login-card">
      <div class="card-glow"></div>

      <div class="lc-header">
        <div class="lc-brand">
          <span class="lc-icon">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <defs>
                <linearGradient id="xbGradientL" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#6554C0" />
                  <stop offset="1" stop-color="#0052CC" />
                </linearGradient>
              </defs>
              <rect width="40" height="40" rx="11" fill="url(#xbGradientL)" />
              <path d="M9 13.5c2.6-1.4 5.6-1.4 8.2 0 .6.3 1 .9 1 1.6v12.3c0 .6-.6 1-1.2.8-2.5-.9-5.3-.9-7.4.3-.4.2-.6-.1-.6-.5V13.5Z" fill="#fff" fill-opacity="0.95"/>
              <path d="M31 13.5c-2.6-1.4-5.6-1.4-8.2 0-.6.3-1 .9-1 1.6v12.3c0 .6.6 1 1.2.8 2.5-.9 5.3-.9 7.4.3.4.2.6-.1.6-.5V13.5Z" fill="#fff" fill-opacity="0.78"/>
              <path d="M20 11.2l1.3 3.2 3.2 1.3-3.2 1.3-1.3 3.2-1.3-3.2-3.2-1.3 3.2-1.3 1.3-3.2Z" fill="#fff"/>
            </svg>
          </span>
          <span class="lc-name">学伴</span>
        </div>
        <h2>{{ isRegister ? '创建账号' : '欢迎回来' }}</h2>
        <p class="muted">{{ isRegister ? '加入学伴，开启智能学习之旅' : '登录后继续你的学习旅程' }}</p>
      </div>

      <el-form @submit.prevent="submit">
        <template v-if="isRegister">
          <el-form-item><el-input v-model="registerForm.username" placeholder="用户名" size="large" /></el-form-item>
          <el-form-item><el-input v-model="registerForm.phone" placeholder="手机号" size="large" /></el-form-item>
          <el-form-item><el-input v-model="registerForm.email" placeholder="邮箱" size="large" /></el-form-item>
          <el-form-item>
            <div class="code-row">
              <el-input v-model="registerForm.code" placeholder="验证码" size="large" />
              <el-button size="large" @click="sendRegisterCode">{{ codeSending ? `${codeCountdown}s` : '获取验证码' }}</el-button>
            </div>
          </el-form-item>
          <el-form-item>
            <el-input v-model="registerForm.password" type="password" placeholder="至少 6 位密码" show-password size="large" />
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item>
            <div class="login-tabs">
              <span :class="['tab-btn', { active: loginTab === 'password' }]" @click="loginTab = 'password'">密码登录</span>
              <span :class="['tab-btn', { active: loginTab === 'code' }]" @click="loginTab = 'code'">验证码登录</span>
            </div>
          </el-form-item>
          <template v-if="loginTab === 'password'">
            <el-form-item><el-input v-model="account" placeholder="用户名 / 邮箱" size="large" /></el-form-item>
            <el-form-item><el-input v-model="password" type="password" placeholder="密码" show-password size="large" /></el-form-item>
          </template>
          <template v-else>
            <el-form-item><el-input v-model="phoneLogin.phone" placeholder="手机号" size="large" /></el-form-item>
            <el-form-item>
              <div class="code-row">
                <el-input v-model="phoneLogin.code" placeholder="验证码" size="large" />
                <el-button size="large" @click="handleSendLoginCode">{{ loginCodeSending ? `${loginCodeCountdown}s` : '获取验证码' }}</el-button>
              </div>
            </el-form-item>
          </template>
        </template>
        <el-form-item>
          <el-button type="primary" class="full" size="large" @click="submit" :loading="submitting">
            {{ isRegister ? '注册' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div class="toggle-row">
        <span class="muted">{{ isRegister ? '已有账号？' : '没有账号？' }}</span>
        <el-button link type="primary" @click="toggleMode">
          {{ isRegister ? '去登录' : '立即注册' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { sendCode, sendLoginCode as sendLoginCodeApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

if (userStore.isLoggedIn) {
  router.replace(String(route.query.redirect || '/'))
}

const isRegister = ref(false)
const loginTab = ref('password')
const account = ref('')
const password = ref('')
const submitting = ref(false)
const codeSending = ref(false)
const codeCountdown = ref(0)
const loginCodeSending = ref(false)
const loginCodeCountdown = ref(0)

const registerForm = reactive({
  username: '',
  phone: '',
  email: '',
  password: '',
  code: '',
})

const phoneLogin = reactive({
  phone: '',
  code: '',
})

function toggleMode() { isRegister.value = !isRegister.value; loginTab.value = 'password' }

let countdownTimer: ReturnType<typeof setInterval> | null = null
function startCodeCountdown(cb: () => void) {
  codeCountdown.value = 60
  codeSending.value = true
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    codeCountdown.value--
    if (codeCountdown.value <= 0) {
      clearInterval(countdownTimer!)
      countdownTimer = null
      codeSending.value = false
      cb()
    }
  }, 1000)
}

function startLoginCodeCountdown() {
  loginCodeCountdown.value = 60
  loginCodeSending.value = true
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    loginCodeCountdown.value--
    if (loginCodeCountdown.value <= 0) {
      clearInterval(countdownTimer!)
      countdownTimer = null
      loginCodeSending.value = false
    }
  }, 1000)
}

async function sendRegisterCode() {
  const target = registerForm.phone || registerForm.email
  if (!target) { ElMessage.warning('请先填写邮箱或手机号'); return }
  codeSending.value = true
  try {
    const result = await sendCode({ target })
    if (result.code) {
      registerForm.code = result.code
      ElMessage.success(`验证码已发送（模拟模式），请填写：${result.code}`)
    } else {
      ElMessage.success(`验证码已发送至 ${target}`)
    }
    startCodeCountdown(() => { codeSending.value = false })
  } catch {
    // interceptor already showed error
  } finally {
    if (!countdownTimer) codeSending.value = false
  }
}

async function handleSendLoginCode() {
  const target = phoneLogin.phone
  if (!target) { ElMessage.warning('请先填写手机号'); return }
  loginCodeSending.value = true
  try {
    const result = await sendLoginCodeApi({ target })
    if (result.code) {
      phoneLogin.code = result.code
      ElMessage.success(`验证码已发送（模拟模式），请填写：${result.code}`)
    } else {
      ElMessage.success(`验证码已发送至 ${target}`)
    }
    startLoginCodeCountdown()
  } catch {
    // interceptor already showed error
  } finally {
    if (!countdownTimer) loginCodeSending.value = false
  }
}

async function submit() {
  submitting.value = true
  try {
    if (isRegister.value) {
      // Client-side validation
      if (!registerForm.username.trim() || !registerForm.phone.trim() || !registerForm.email.trim() || !registerForm.code.trim() || !registerForm.password.trim()) {
        ElMessage.warning('请填写所有必填字段')
        submitting.value = false
        return
      }
      if (registerForm.password.length < 6) {
        ElMessage.warning('密码至少 6 位')
        submitting.value = false
        return
      }
      await userStore.registerAccount(registerForm)
      ElMessage.success('注册成功，请登录')
      isRegister.value = false
    } else if (loginTab.value === 'password') {
      await userStore.loginByPassword(account.value, password.value)
      router.push(String(route.query.redirect || '/'))
    } else {
      await userStore.loginByPhoneCode(phoneLogin.phone, phoneLogin.code)
      router.push(String(route.query.redirect || '/'))
    }
  } catch {
    // error message handled by request interceptor
  } finally {
    submitting.value = false
  }
}

/* ===== Canvas Particle System ===== */
const canvasRef = ref<HTMLCanvasElement | null>(null)
let animId = 0

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  alpha: number
  alphaSpeed: number
  hue: number
}

const COLORS = [
  { h: 120, s: '80%', l: '55%' },  // green
  { h: 140, s: '90%', l: '50%' },  // fluorescent green
  { h: 160, s: '75%', l: '55%' },  // teal green
  { h: 100, s: '70%', l: '50%' },  // lime green
]

let mouse = { x: -1000, y: -1000, vx: 0, vy: 0 }
let particles: Particle[] = []
let ctx: CanvasRenderingContext2D | null = null
let canvasW = 0
let canvasH = 0

function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  if (!ctx) return

  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('touchmove', onTouchMove, { passive: true })

  createParticles()
  animate()
}

function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  canvasW = window.innerWidth
  canvasH = window.innerHeight
  canvas.width = canvasW * devicePixelRatio
  canvas.height = canvasH * devicePixelRatio
  if (ctx) {
    ctx.scale(devicePixelRatio, devicePixelRatio)
    canvas.style.width = canvasW + 'px'
    canvas.style.height = canvasH + 'px'
  }
}

function onMouseMove(e: MouseEvent) {
  mouse.vx = (e.clientX - mouse.x) * 0.08
  mouse.vy = (e.clientY - mouse.y) * 0.08
  mouse.x = e.clientX
  mouse.y = e.clientY
}

function onTouchMove(e: TouchEvent) {
  const t = e.touches[0]
  if (t) {
    mouse.vx = (t.clientX - mouse.x) * 0.08
    mouse.vy = (t.clientY - mouse.y) * 0.08
    mouse.x = t.clientX
    mouse.y = t.clientY
  }
}

function createParticles() {
  particles = []
  const count = Math.min(100, Math.floor(canvasW * canvasH / 15000))
  for (let i = 0; i < count; i++) {
    const color = COLORS[i % COLORS.length]
    const angle = Math.random() * Math.PI * 2
    const speed = Math.random() * 0.4 + 0.2
    particles.push({
      x: Math.random() * canvasW,
      y: Math.random() * canvasH,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      size: Math.random() * 2.5 + 1.2,
      alpha: Math.random() * 0.4 + 0.2,
      alphaSpeed: (Math.random() - 0.5) * 0.006,
      hue: color.h + Math.random() * 20 - 10,
    })
  }
}

function animate() {
  if (!ctx) return
  ctx.clearRect(0, 0, canvasW, canvasH)

  const t = Date.now() * 0.0003

  // Draw aurora wave bands
  drawAurora(t)

  // Draw gradient light orbs (background glow)
  drawOrbs(t)

  // Update & draw particles
  for (let i = 0; i < particles.length; i++) {
    const p = particles[i]
    // Aurora-like wave flow: gentle sine influence on movement
    p.vx += Math.sin(t + p.y * 0.002) * 0.02
    p.vy += Math.cos(t * 0.7 + p.x * 0.002) * 0.02

    // Move
    p.x += p.vx
    p.y += p.vy
    // Boundary wrap
    if (p.x < -30) p.x = canvasW + 30
    if (p.x > canvasW + 30) p.x = -30
    if (p.y < -30) p.y = canvasH + 30
    if (p.y > canvasH + 30) p.y = -30
    // Fade
    p.alpha += p.alphaSpeed
    if (p.alpha > 0.7 || p.alpha < 0.15) p.alphaSpeed *= -1

    // Mouse repulsion + velocity burst
    const dx = mouse.x - p.x
    const dy = mouse.y - p.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (dist < 200 && dist > 0) {
      const force = (200 - dist) / 200 * 0.6
      p.vx -= (dx / dist) * force * 0.04
      p.vy -= (dy / dist) * force * 0.04
      // Add mouse velocity influence for high-speed sweep
      const mouseSpeed = Math.sqrt(mouse.vx * mouse.vx + mouse.vy * mouse.vy)
      if (mouseSpeed > 8) {
        const burst = mouseSpeed * 0.001 * (1 - dist / 200)
        p.vx += (mouse.vx * 0.008 + (dx / dist) * mouseSpeed * 0.02) * burst
        p.vy += (mouse.vy * 0.008 + (dy / dist) * mouseSpeed * 0.02) * burst
      }
      const speed = Math.sqrt(p.vx * p.vx + p.vy * p.vy)
      if (speed > 1.8) {
        p.vx = (p.vx / speed) * 1.8
        p.vy = (p.vy / speed) * 3.0
      }
    }
    // Drag
    p.vx *= 0.985
    p.vy *= 0.985
    // Min speed
    const spd = Math.sqrt(p.vx * p.vx + p.vy * p.vy)
    if (spd < 0.15 && spd > 0) {
      p.vx = (p.vx / spd) * 0.15
      p.vy = (p.vy / spd) * 0.15
    }

    // Draw particle
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
    ctx.fillStyle = `hsla(${p.hue + t * 5 % 360}, 70%, 65%, ${p.alpha})`
    ctx.fill()

    // Glow
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.size * 3.5, 0, Math.PI * 2)
    ctx.fillStyle = `hsla(${p.hue + t * 5 % 360}, 70%, 65%, ${p.alpha * 0.1})`
    ctx.fill()
  }

  // Draw connections
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const a = particles[i]
      const b = particles[j]
      const dx = a.x - b.x
      const dy = a.y - b.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 160) {
        const alpha = (1 - dist / 160) * 0.25
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.strokeStyle = `hsla(${(a.hue + b.hue) / 2 + t * 3 % 360}, 60%, 60%, ${alpha})`
        ctx.lineWidth = 0.6
        ctx.stroke()
      }
    }
  }

  // Mouse velocity burst ring
  const mouseSpeed = Math.sqrt(mouse.vx * mouse.vx + mouse.vy * mouse.vy)
  if (mouseSpeed > 12) {
    const ringAlpha = Math.min(mouseSpeed / 100, 0.15)
    const ringRadius = 20 + Math.min(mouseSpeed, 40)
    ctx.beginPath()
    ctx.arc(mouse.x, mouse.y, ringRadius, 0, Math.PI * 2)
    ctx.strokeStyle = `hsla(140, 80%, 55%, ${ringAlpha})`
    ctx.lineWidth = 1
    ctx.stroke()
    const grd = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, ringRadius)
    grd.addColorStop(0, `hsla(140, 80%, 55%, ${ringAlpha * 0.15})`)
    grd.addColorStop(1, 'hsla(140, 80%, 55%, 0)')
    ctx.fillStyle = grd
    ctx.fillRect(mouse.x - ringRadius, mouse.y - ringRadius, ringRadius * 2, ringRadius * 2)
  }
  // Decay mouse velocity
  mouse.vx *= 0.92
  mouse.vy *= 0.92

  animId = requestAnimationFrame(animate)
}

function drawAurora(t: number) {
  if (!ctx) return
  ctx.save()

  for (let band = 0; band < 3; band++) {
    const offset = band * 2.1
    const hue = 120 + band * 15 + Math.sin(t * 0.1 + band) * 10
    const yBase = canvasH * (0.2 + band * 0.25) + Math.sin(t * 0.15 + band * 2) * canvasH * 0.08

    ctx.beginPath()
    ctx.moveTo(0, yBase)

    for (let x = 0; x <= canvasW; x += 3) {
      const wave = Math.sin(x * 0.005 + t * 0.4 + offset) * 40
        + Math.sin(x * 0.012 + t * 0.6 + offset * 0.7) * 20
        + Math.sin(x * 0.002 + t * 0.2 + band) * 60
      const y = yBase + wave
      ctx.lineTo(x, y)
    }

    // Bottom edge back
    for (let x = canvasW; x >= 0; x -= 3) {
      const wave = Math.sin(x * 0.005 + t * 0.4 + offset + 1) * 40
        + Math.sin(x * 0.012 + t * 0.6 + offset * 0.7 + 1) * 20
        + Math.sin(x * 0.002 + t * 0.2 + band + 1) * 60
      const y = yBase + wave + 50 + Math.sin(t * 0.1 + band) * 20
      ctx.lineTo(x, y)
    }
    ctx.closePath()

    const grad = ctx.createLinearGradient(0, yBase - 60, 0, yBase + 80)
    grad.addColorStop(0, `hsla(${hue}, 70%, 55%, 0)`)
    grad.addColorStop(0.3, `hsla(${hue}, 70%, 55%, 0.04)`)
    grad.addColorStop(0.5, `hsla(${hue}, 70%, 55%, 0.06)`)
    grad.addColorStop(0.7, `hsla(${hue}, 70%, 55%, 0.04)`)
    grad.addColorStop(1, `hsla(${hue}, 70%, 55%, 0)`)
    ctx.fillStyle = grad
    ctx.fill()
  }

  ctx.restore()
}

function drawOrbs(t: number) {
  if (!ctx) return

  // Orb 1 - fluorescent green, top-left
  const o1x = canvasW * 0.15 + Math.sin(t * 0.7) * canvasW * 0.12
  const o1y = canvasH * 0.2 + Math.cos(t * 0.6) * canvasH * 0.1
  const r1 = Math.min(canvasW, canvasH) * 0.4
  const g1 = ctx.createRadialGradient(o1x, o1y, 0, o1x, o1y, r1)
  g1.addColorStop(0, 'hsla(130, 80%, 55%, 0.15)')
  g1.addColorStop(0.4, 'hsla(130, 80%, 55%, 0.07)')
  g1.addColorStop(1, 'hsla(130, 80%, 55%, 0)')
  ctx.fillStyle = g1
  ctx.fillRect(0, 0, canvasW, canvasH)

  // Orb 2 - bright green, bottom-right
  const o2x = canvasW * 0.85 + Math.sin(t * 0.8 + 1) * canvasW * 0.1
  const o2y = canvasH * 0.8 + Math.cos(t * 0.5 + 2) * canvasH * 0.1
  const r2 = Math.min(canvasW, canvasH) * 0.35
  const g2 = ctx.createRadialGradient(o2x, o2y, 0, o2x, o2y, r2)
  g2.addColorStop(0, 'hsla(145, 90%, 50%, 0.12)')
  g2.addColorStop(0.4, 'hsla(145, 90%, 50%, 0.06)')
  g2.addColorStop(1, 'hsla(145, 90%, 50%, 0)')
  ctx.fillStyle = g2
  ctx.fillRect(0, 0, canvasW, canvasH)

  // Orb 3 - lime green, center
  const o3x = canvasW * 0.5 + Math.sin(t * 0.4 + 3) * canvasW * 0.15
  const o3y = canvasH * 0.45 + Math.cos(t * 0.7 + 4) * canvasH * 0.12
  const r3 = Math.min(canvasW, canvasH) * 0.3
  const g3 = ctx.createRadialGradient(o3x, o3y, 0, o3x, o3y, r3)
  g3.addColorStop(0, 'hsla(110, 75%, 55%, 0.1)')
  g3.addColorStop(0.5, 'hsla(110, 75%, 55%, 0.05)')
  g3.addColorStop(1, 'hsla(110, 75%, 55%, 0)')
  ctx.fillStyle = g3
  ctx.fillRect(0, 0, canvasW, canvasH)

  // Orb 4 - teal, bottom-left
  const o4x = canvasW * 0.3 + Math.sin(t * 0.55 + 5) * canvasW * 0.08
  const o4y = canvasH * 0.7 + Math.cos(t * 0.9 + 6) * canvasH * 0.08
  const r4 = Math.min(canvasW, canvasH) * 0.22
  const g4 = ctx.createRadialGradient(o4x, o4y, 0, o4x, o4y, r4)
  g4.addColorStop(0, 'hsla(165, 70%, 50%, 0.08)')
  g4.addColorStop(1, 'hsla(165, 70%, 50%, 0)')
  ctx.fillStyle = g4
  ctx.fillRect(0, 0, canvasW, canvasH)
}

onMounted(() => {
  initCanvas()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  window.removeEventListener('resize', resizeCanvas)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('touchmove', onTouchMove)
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
})
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: #080c24;
  padding: 24px;
  position: relative;
  overflow: hidden;
}

.particle-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

/* ===== Card ===== */
.login-card {
  width: 420px;
  background: rgba(16, 20, 44, 0.82);
  backdrop-filter: blur(28px) saturate(1.5);
  -webkit-backdrop-filter: blur(28px) saturate(1.5);
  border-radius: var(--radius-xl);
  padding: 40px 36px;
  border: 1px solid rgba(101, 84, 192, 0.18);
  position: relative;
  z-index: 1;
  animation: card-rise 0.9s cubic-bezier(0.16, 1, 0.3, 1) both;
  box-shadow:
    0 8px 40px rgba(0, 0, 0, 0.5),
    0 0 100px rgba(101, 84, 192, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}
@keyframes card-rise {
  from { opacity: 0; transform: translateY(40px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* Card glow border */
.card-glow {
  position: absolute;
  inset: -1px;
  border-radius: var(--radius-xl);
  padding: 1px;
  background: linear-gradient(
    var(--glow-angle, 0deg),
    rgba(101, 84, 192, 0.35),
    transparent 35%,
    transparent 65%,
    rgba(0, 82, 204, 0.25)
  );
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  -webkit-mask-composite: xor;
  pointer-events: none;
  z-index: -1;
  animation: glow-rotate 7s linear infinite;
}
@keyframes glow-rotate {
  to { --glow-angle: 360deg; }
}
@property --glow-angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}

.lc-header { text-align: center; margin-bottom: 28px; }
.lc-brand {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  margin-bottom: 20px;
}
.lc-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 40px; height: 40px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(101, 84, 192, 0.4);
  animation: icon-float 3s ease-in-out infinite;
}
@keyframes icon-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}
.lc-icon svg { width: 100%; height: 100%; display: block; }
.lc-name {
  font-size: 22px;
  font-weight: 800;
  background: linear-gradient(135deg, #6554C0, #0052CC);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.lc-header h2 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: #e8eaf6;
}
.lc-header p {
  font-size: 14px;
  margin: 0;
  color: rgba(200, 200, 230, 0.55);
}

.full { width: 100%; }
.code-row { display: grid; grid-template-columns: 1fr 130px; gap: 10px; width: 100%; }
.login-tabs { display: flex; width: 100%; border-radius: 10px; overflow: hidden; border: 1px solid rgba(101, 84, 192, 0.15); }
.tab-btn {
  flex: 1; text-align: center; padding: 10px 0; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: all 0.3s; color: rgba(200, 200, 230, 0.45);
  background: rgba(22, 28, 58, 0.4);
}
.tab-btn.active { color: #e8eaf6; background: rgba(101, 84, 192, 0.25); }
.tab-btn:not(.active):hover { color: rgba(200, 200, 230, 0.7); }
.toggle-row {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  color: rgba(200, 200, 230, 0.55);
}
.toggle-row :deep(.el-button) {
  color: #e8eaf6;
  font-weight: 600;
  background: none transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 4px;
}
.toggle-row :deep(.el-button:hover) {
  color: #ffffff;
}

:deep(.el-input__wrapper) {
  border-radius: 12px;
  background: rgba(22, 28, 58, 0.6);
  border: 1px solid rgba(101, 84, 192, 0.12);
  box-shadow: none;
  transition: all 0.3s;
}
:deep(.el-input__wrapper:hover) {
  border-color: rgba(101, 84, 192, 0.3);
}
:deep(.el-input__wrapper.is-focus) {
  border-color: rgba(101, 84, 192, 0.5);
  box-shadow: 0 0 0 3px rgba(101, 84, 192, 0.12), 0 0 24px rgba(101, 84, 192, 0.08);
  background: rgba(22, 28, 58, 0.8);
}
:deep(.el-input__inner) {
  color: #e8eaf6;
}
:deep(.el-input__inner::placeholder) {
  color: rgba(200, 200, 230, 0.35);
}
:deep(.el-select .el-input__wrapper) {
  border-radius: 12px;
  background: rgba(22, 28, 58, 0.6);
  border: 1px solid rgba(101, 84, 192, 0.12);
}
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #6554C0, #0052CC);
  border: none;
  border-radius: 12px;
  font-weight: 600;
  box-shadow: 0 4px 20px rgba(101, 84, 192, 0.3);
  transition: all 0.3s;
}
:deep(.el-button--primary:hover) {
  box-shadow: 0 6px 28px rgba(101, 84, 192, 0.45);
  transform: translateY(-2px);
}
:deep(.el-button--primary:active) {
  transform: translateY(0);
}
:deep(.el-button--primary.is-loading::before) {
  background: none;
  box-shadow: none;
}

.muted { color: rgba(200, 200, 230, 0.45); }

@media (max-width: 480px) {
  .login-card { padding: 28px 20px; width: 100%; }
}
</style>
