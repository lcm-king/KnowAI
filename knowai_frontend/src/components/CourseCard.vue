<template>
  <RouterLink class="course-card" :to="`/courses/${course.id}`">
    <div class="card-cover">
      <el-image class="cover-img" :src="course.cover || ''" fit="cover">
        <template #error>
          <div class="cover-fallback">
            <span class="material-symbols-outlined">school</span>
          </div>
        </template>
      </el-image>
      <span v-if="course.seckill_price" class="badge badge-seckill">
        <span class="material-symbols-outlined">local_fire_department</span> 秒杀
      </span>
      <span v-else-if="(course.rating || 0) >= 4.7" class="badge badge-ai">
        <span class="material-symbols-outlined">auto_awesome</span> AI 推荐
      </span>
      <span v-else-if="(course.learn_count || 0) > 500" class="badge badge-hot">热门</span>
      <FavoriteButton :course-id="course.id" variant="overlay" class="fav-corner" />
    </div>
    <div class="card-body">
      <h3 class="card-title">{{ course.title }}</h3>
      <div class="card-meta">
        <span class="meta-category">{{ course.category || '综合' }}</span>
        <span class="meta-rating">
          <span class="material-symbols-outlined star">star</span>
          {{ course.rating?.toFixed(1) }}
        </span>
        <span class="meta-learners">{{ course.learn_count || 0 }} 人学习</span>
      </div>
      <div class="card-footer">
        <span v-if="course.seckill_price" class="price seckill-price">
          ¥{{ course.seckill_price }}
        </span>
        <span v-else-if="isFree" class="price free-price">免费</span>
        <span v-else class="price">查看详情</span>
        <span class="arrow material-symbols-outlined">arrow_forward</span>
      </div>
    </div>
  </RouterLink>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Course } from '@/api/courses'
import FavoriteButton from './FavoriteButton.vue'

const props = defineProps<{ course: Course }>()
const isFree = computed(() => {
  if (!props.course.skus || props.course.skus.length === 0) return false
  return props.course.skus.every(s => Number(s.price) === 0)
})
</script>

<style scoped>
.course-card {
  display: block;
  background: var(--surface-container-lowest);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--elev-1);
  border: 1px solid var(--outline-variant);
  transition: all 0.32s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}
.course-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: var(--radius-lg);
  padding: 2px;
  background: var(--ai-gradient);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
  z-index: 1;
}
.course-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(9, 30, 66, 0.18);
}
.course-card:hover::before { opacity: 1; }

.card-cover {
  position: relative;
  height: 170px;
  overflow: hidden;
}
.cover-img {
  width: 100%;
  height: 100%;
  transition: transform 0.55s cubic-bezier(0.16, 1, 0.3, 1);
}
.course-card:hover .cover-img { transform: scale(1.1); }

.card-cover::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(15, 27, 66, 0.35), transparent 50%);
  opacity: 0;
  transition: opacity 0.3s;
}
.course-card:hover .card-cover::after { opacity: 1; }

.badge {
  position: absolute;
  top: 12px;
  left: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  z-index: 2;
  backdrop-filter: blur(8px);
}
.badge .material-symbols-outlined { font-size: 14px; }
.badge-seckill {
  background: rgba(255, 86, 48, 0.92);
  color: #fff;
  animation: badge-shake 3s ease-in-out infinite;
}
.badge-ai {
  background: var(--ai-gradient);
  color: #fff;
  box-shadow: 0 0 0 0 rgba(101, 84, 192, 0.5);
  animation: badge-ai-pulse 2.4s ease-out infinite;
}
@keyframes badge-shake {
  0%, 88%, 100% { transform: translateX(0) rotate(0); }
  91% { transform: translateX(-2px) rotate(-3deg); }
  94% { transform: translateX(2px) rotate(3deg); }
  97% { transform: translateX(-1px) rotate(-2deg); }
}
@keyframes badge-ai-pulse {
  0% { box-shadow: 0 0 0 0 rgba(101, 84, 192, 0.5); }
  70% { box-shadow: 0 0 0 8px rgba(101, 84, 192, 0); }
  100% { box-shadow: 0 0 0 0 rgba(101, 84, 192, 0); }
}
.badge-hot {
  background: rgba(255, 171, 0, 0.92);
  color: #5a3a00;
}

.fav-corner {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 3;
}

.card-body {
  padding: 16px;
  position: relative;
  z-index: 2;
}
.card-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--on-surface);
  transition: color 0.2s;
}
.course-card:hover .card-title { color: var(--primary); }

.card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--on-surface-variant);
}
.meta-category {
  background: var(--surface-container-low);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
}
.star { font-size: 14px; color: var(--warning); }
.meta-learners { margin-left: auto; }

.card-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--outline-variant);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.price {
  font-size: 16px;
  font-weight: 700;
  color: var(--primary);
}
.seckill-price { color: var(--danger); }
.arrow {
  font-size: 18px;
  color: var(--outline);
  transition: transform 0.25s, color 0.2s;
}
.course-card:hover .arrow {
  transform: translateX(6px);
  color: var(--primary);
}
.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--primary-container), var(--secondary-container));
}
.cover-fallback .material-symbols-outlined {
  font-size: 56px;
  opacity: 0.5;
  color: var(--on-primary-container);
}
.free-price {
  color: var(--tertiary);
}
</style>
