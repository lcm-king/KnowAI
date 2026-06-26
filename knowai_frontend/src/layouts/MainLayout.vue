<template>
  <div :class="{ dark: darkMode }">
    <header class="nav">
      <div class="nav-inner">
        <div class="nav-left">
          <RouterLink class="brand" to="/">
            <span class="brand-icon">
              <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <defs>
                  <linearGradient id="xbGradient" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#6554C0" />
                    <stop offset="1" stop-color="#0052CC" />
                  </linearGradient>
                </defs>
                <rect width="40" height="40" rx="11" fill="url(#xbGradient)" />
                <path d="M9 13.5c2.6-1.4 5.6-1.4 8.2 0 .6.3 1 .9 1 1.6v12.3c0 .6-.6 1-1.2.8-2.5-.9-5.3-.9-7.4.3-.4.2-.6-.1-.6-.5V13.5Z" fill="#fff" fill-opacity="0.95"/>
                <path d="M31 13.5c-2.6-1.4-5.6-1.4-8.2 0-.6.3-1 .9-1 1.6v12.3c0 .6.6 1 1.2.8 2.5-.9 5.3-.9 7.4.3.4.2.6-.1.6-.5V13.5Z" fill="#fff" fill-opacity="0.78"/>
                <path d="M20 11.2l1.3 3.2 3.2 1.3-3.2 1.3-1.3 3.2-1.3-3.2-3.2-1.3 3.2-1.3 1.3-3.2Z" fill="#fff"/>
              </svg>
            </span>
            <span class="brand-text">学伴</span>
          </RouterLink>
          <nav class="desktop-only nav-links">
            <RouterLink to="/courses" class="nav-link">全部课程</RouterLink>
            <RouterLink v-if="userStore.isLoggedIn" to="/my-courses" class="nav-link">我的学习</RouterLink>
            <RouterLink v-if="userStore.role === 'teacher'" to="/teacher" class="nav-link nav-link--accent">讲师后台</RouterLink>
            <RouterLink v-if="userStore.role === 'admin'" to="/admin" class="nav-link nav-link--accent">管理后台</RouterLink>
          </nav>
        </div>

        <div class="nav-right">
          <div class="desktop-only search-box">
            <span class="material-symbols-outlined search-icon">search</span>
            <input
              v-model="searchText"
              class="search-input"
              placeholder="搜索 AI 课程..."
              @keyup.enter="goSearch"
            />
            <button v-if="searchText" class="ai-search-btn" @click="goSearch">
              <span class="material-symbols-outlined">auto_awesome</span>
            </button>
          </div>

          <div class="actions">
            <el-switch v-model="darkMode" inline-prompt active-text="暗" inactive-text="亮" size="small" />

            <RouterLink to="/cart" class="icon-btn">
              <el-badge :value="cartStore.count" :hidden="cartStore.count === 0">
                <span class="material-symbols-outlined">shopping_cart</span>
              </el-badge>
            </RouterLink>

            <RouterLink v-if="!userStore.isLoggedIn" to="/login">
              <el-button type="primary" class="btn-login">登录</el-button>
            </RouterLink>

            <el-dropdown v-else>
              <button class="avatar-btn">
                <span class="avatar">{{ (userStore.user?.username || 'U')[0].toUpperCase() }}</span>
                <span class="desktop-only username-text">{{ userStore.user?.username || '用户' }}</span>
                <span class="material-symbols-outlined chevron">expand_more</span>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="$router.push('/profile')">个人中心</el-dropdown-item>
                  <el-dropdown-item @click="$router.push('/my-courses')">我的课程</el-dropdown-item>
                  <el-dropdown-item @click="$router.push('/orders')">我的订单</el-dropdown-item>
                  <el-dropdown-item divided @click="userStore.logout()">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </header>

    <el-progress v-if="loadingStore.loading" :percentage="100" :show-text="false" status="success" :duration="1" />

    <main><RouterView /></main>

    <AiAssistant />
  </div>
</template>

<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import AiAssistant from '@/components/AiAssistant.vue'
import { useCartStore } from '@/stores/cart'
import { useLoadingStore } from '@/stores/loading'
import { useUserStore } from '@/stores/user'

const darkMode = ref(false)
const cartStore = useCartStore()
const loadingStore = useLoadingStore()
const userStore = useUserStore()
const router = useRouter()
const searchText = ref('')

watchEffect(() => {
  document.documentElement.classList.toggle('dark', darkMode.value)
})

function goSearch() {
  const q = searchText.value.trim()
  if (q) {
    router.push(`/courses?keyword=${encodeURIComponent(q)}`)
  }
}

if (userStore.isLoggedIn) {
  cartStore.refresh().catch(() => undefined)
}
</script>

<style scoped>
.nav {
  position: sticky;
  top: 0;
  z-index: 50;
  height: 68px;
  background: var(--surface-container-lowest);
  border-bottom: 1px solid var(--outline-variant);
  box-shadow: 0 1px 4px rgba(9, 30, 66, 0.06);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.nav-inner {
  max-width: var(--container-max);
  margin: 0 auto;
  padding: 0 var(--gutter);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.nav-left { display: flex; align-items: center; gap: 28px; }
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 22px;
  color: var(--primary);
}
.brand-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  overflow: hidden;
}
.brand-icon svg { width: 100%; height: 100%; display: block; }
.brand-text { letter-spacing: -0.02em; }

.nav-links { display: flex; gap: 6px; }
.nav-link {
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: var(--on-surface-variant);
  transition: all 0.18s ease;
}
.nav-link:hover { color: var(--primary); background: var(--surface-container-low); }
.nav-link.router-link-active { color: var(--primary); background: var(--surface-container-low); }
.nav-link.nav-link--accent { color: var(--secondary); }
.nav-link.nav-link--accent:hover { background: var(--ai-gradient-soft); color: var(--secondary); }

.nav-right { display: flex; align-items: center; gap: 14px; }

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  width: 260px;
  height: 42px;
  border-radius: 24px;
  background: var(--surface-container-low);
  border: 1px solid var(--outline-variant);
  transition: all 0.22s ease;
}
.search-box:focus-within {
  width: 300px;
  border-color: var(--secondary);
  box-shadow: 0 0 0 3px rgba(101, 84, 192, 0.12);
  background: var(--surface-container-lowest);
}
.search-icon {
  position: absolute;
  left: 12px;
  font-size: 20px;
  color: var(--outline);
  pointer-events: none;
}
.search-input {
  flex: 1;
  height: 100%;
  padding: 0 38px;
  background: transparent;
  border: none;
  outline: none;
  font-size: 14px;
  color: var(--on-surface);
  font-family: inherit;
}
.search-input::placeholder { color: var(--outline); }
.ai-search-btn {
  position: absolute;
  right: 4px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--ai-gradient);
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
}
.ai-search-btn:hover { transform: scale(1.1); }
.ai-search-btn .material-symbols-outlined { font-size: 16px; }

.actions { display: flex; align-items: center; gap: 10px; }
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  color: var(--on-surface-variant);
  transition: all 0.18s;
}
.icon-btn:hover { background: var(--surface-container-low); color: var(--primary); }
.icon-btn .material-symbols-outlined { font-size: 22px; }

.btn-login { font-weight: 600; font-size: 14px; border-radius: 10px; padding: 10px 20px; }

.avatar-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  border-radius: 14px;
  background: transparent;
  border: 1px solid var(--outline-variant);
  cursor: pointer;
  transition: all 0.18s;
  font-family: inherit;
  color: var(--on-surface);
}
.avatar-btn:hover { background: var(--surface-container-low); border-color: var(--primary); }
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: var(--ai-gradient);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
}
.username-text { font-size: 14px; font-weight: 500; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chevron { font-size: 18px; color: var(--outline); }

:deep(.el-progress-bar__outer) { border-radius: 0; height: 3px; }

@media (max-width: 900px) {
  .nav { height: 60px; }
  .nav-inner { gap: 10px; padding: 0 16px; }
  .brand-text { display: none; }
  .brand-icon { width: 32px; height: 32px; font-size: 16px; }
  .username-text { display: none; }
}
</style>
