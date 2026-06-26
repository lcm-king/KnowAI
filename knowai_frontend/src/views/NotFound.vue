<template>
  <div class="not-found">
    <div class="nf-inner">
      <div class="nf-code">
        <span>4</span>
        <span class="nf-zero">0</span>
        <span>4</span>
      </div>
      <h2 class="nf-title">页面走丢了</h2>
      <p class="nf-desc">您访问的页面不存在或已被移除，请检查地址是否正确。</p>
      <div class="nf-actions">
        <RouterLink to="/" class="btn-ai">返回首页</RouterLink>
        <RouterLink to="/courses" class="nf-link">浏览课程 <span class="material-symbols-outlined">arrow_forward</span></RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 80vh;
  display: grid;
  place-items: center;
  padding: 48px 24px;
}
.nf-inner { text-align: center; max-width: 540px; }
.nf-code {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  font-size: 120px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.04em;
  background: var(--ai-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 16px;
}
.nf-zero { animation: nf-pulse 2s ease-in-out infinite; }
@keyframes nf-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.08); opacity: 0.7; }
}
.nf-title { font-size: 28px; font-weight: 700; margin: 0 0 12px; }
.nf-desc { color: var(--on-surface-variant); font-size: 15px; margin: 0 0 28px; }
.nf-actions { display: flex; align-items: center; justify-content: center; gap: 20px; flex-wrap: wrap; }
.nf-link {
  color: var(--primary);
  font-weight: 600;
  display: inline-flex; align-items: center; gap: 4px;
}
.nf-link .material-symbols-outlined { font-size: 18px; transition: transform 0.2s; }
.nf-link:hover .material-symbols-outlined { transform: translateX(4px); }
</style>
