<template>
  <div class="container">
    <h1 class="page-title">购物车</h1>
    <div v-if="!cartStore.items.length" class="empty-state">
      <span class="material-symbols-outlined">shopping_cart</span>
      <p>购物车还是空的</p>
      <RouterLink to="/courses" class="btn-ai">去逛逛</RouterLink>
    </div>
    <template v-else>
      <div class="cart-table panel">
        <table>
          <thead>
            <tr>
              <th>课程</th>
              <th>版本</th>
              <th>价格</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in cartStore.items" :key="item.sku_id">
              <td class="td-course">{{ item.course_title }}</td>
              <td>{{ item.sku_name || '标准版' }}</td>
              <td class="td-price">¥{{ item.price }}</td>
              <td>
                <button class="remove-btn" @click="cartStore.remove(item.sku_id)">
                  <span class="material-symbols-outlined">delete</span> 删除
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="checkout-bar">
        <div class="cb-total">
          合计 <span class="cb-amount">¥{{ cartStore.totalAmount.toFixed(2) }}</span>
          <span class="cb-count">({{ cartStore.items.length }} 门课程)</span>
        </div>
        <button class="btn-ai" :disabled="checkingOut" @click="checkout">
          <span class="material-symbols-outlined">payment</span> {{ checkingOut ? '提交中...' : '去结算' }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createOrder } from '@/api/orders'
import { useCartStore } from '@/stores/cart'

const router = useRouter()
const cartStore = useCartStore()
const checkingOut = ref(false)

async function checkout() {
  if (!cartStore.items.length) {
    ElMessage.warning('购物车为空，请先选择课程')
    return
  }
  if (checkingOut.value) return
  checkingOut.value = true
  try {
    const order = await createOrder(cartStore.items.map((item) => item.sku_id))
    if (order.direct_granted) {
      ElMessage.success('免费课程已加入我的学习')
      router.push('/my-courses')
    } else if (order.order_sns && order.order_sns.length > 1) {
      ElMessage.success(`已创建 ${order.order_sns.length} 笔订单，请逐笔支付`)
      router.push(`/pay/${order.order_sn}?sns=${order.order_sns.join(',')}`)
    } else {
      router.push(`/pay/${order.order_sn}`)
    }
  } catch {
    ElMessage.error('下单失败，请稍后再试')
  } finally {
    checkingOut.value = false
  }
}

onMounted(() => cartStore.refresh())
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: var(--on-surface-variant);
}
.empty-state .material-symbols-outlined { font-size: 64px; opacity: 0.4; }
.empty-state p { font-size: 15px; margin: 12px 0 24px; }

.cart-table { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th {
  text-align: left;
  padding: 14px 16px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--on-surface-variant);
  border-bottom: 2px solid var(--outline-variant);
}
td { padding: 16px; border-bottom: 1px solid var(--outline-variant); font-size: 14px; color: var(--on-surface); }
.td-course { font-weight: 600; }
.td-price { font-weight: 700; color: var(--primary); }
.remove-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 6px 12px;
  border-radius: var(--radius);
  background: transparent;
  border: 1px solid var(--outline-variant);
  color: var(--danger);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.remove-btn:hover { background: rgba(255, 86, 48, 0.08); border-color: var(--danger); }
.remove-btn .material-symbols-outlined { font-size: 16px; }

.checkout-bar {
  display: flex; align-items: center; justify-content: flex-end;
  gap: 24px;
  margin-top: 24px;
  padding: 20px;
  background: var(--surface-container-lowest);
  border: 1px solid var(--outline-variant);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev-1);
}
.cb-total { font-size: 16px; color: var(--on-surface-variant); }
.cb-amount { font-size: 28px; font-weight: 800; color: var(--on-surface); margin-left: 8px; }
.cb-count { font-size: 13px; color: var(--on-surface-variant); margin-left: 6px; }
.btn-ai:disabled { opacity: 0.6; cursor: not-allowed; }
</style>