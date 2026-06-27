<template>
  <div class="container">
    <h1 class="page-title">支付订单</h1>
    <div class="panel">
      <div v-if="allOrderSns.length > 1" class="multi-badge">
        共 {{ allOrderSns.length }} 笔订单，当前第 {{ currentIndex + 1 }} 笔
      </div>
      <div v-if="orderAmount" class="amount-row">
        <span class="amount-label">支付金额：</span>
        <span class="amount-value">¥{{ orderAmount }}</span>
      </div>
      <el-radio-group v-model="method">
        <el-radio-button label="wechat">微信</el-radio-button>
        <el-radio-button label="alipay">支付宝</el-radio-button>
      </el-radio-group>
      <div class="pay-box">
        <el-button v-if="!payInfo" type="primary" @click="pay" :loading="loading">去支付</el-button>

        <p v-if="paid" class="success-hint">{{ allPaid ? '全部支付成功！' : '支付成功！' }}</p>
        <p v-else-if="payInfo?.mock && method === 'wechat'" class="mock-hint">微信支付</p>
        <p v-else-if="payInfo && !payInfo.qr_code_url && !payInfo?.mock" class="error">创建支付失败，请重试</p>

        <div v-if="payInfo?.qr_code_url && !paid" class="qr-wrapper">
          <p class="qr-tip">{{ method === 'wechat' ? '请使用微信扫码支付' : '请使用支付宝扫码支付' }}</p>
          <el-image :src="payInfo.qr_code_url" style="width:220px;height:220px" fit="contain" />
        </div>
      </div>
      <p class="pay-hint">暂仅支持微信 / 支付宝支付</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createPay, getOrder } from '@/api/orders'
import { request } from '@/api/request'

const route = useRoute()
const router = useRouter()
const method = ref<'wechat' | 'alipay'>('wechat')
const payInfo = ref<Awaited<ReturnType<typeof createPay>>>()
const loading = ref(false)
const paid = ref(false)
const orderAmount = ref<string>('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const allOrderSns = computed(() => {
  const sns = route.query.sns as string | undefined
  return sns ? sns.split(',') : [String(route.params.orderSn)]
})
const currentIndex = computed(() => allOrderSns.value.indexOf(route.params.orderSn as string))
const allPaid = ref(false)

onMounted(async () => {
  try {
    const order = await getOrder(String(route.params.orderSn))
    orderAmount.value = order.pay_amount
  } catch {
    // ignore
  }
})

async function pay() {
  loading.value = true
  try {
    payInfo.value = await createPay(String(route.params.orderSn), method.value)
    startPoll()
  } finally {
    loading.value = false
  }
}

async function startPoll() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    try {
      const res = await request.get<unknown, { paid: boolean }>(`/pay/status/${route.params.orderSn}`)
      if (res.paid) {
        paid.value = true
        if (pollTimer) clearInterval(pollTimer)
        pollTimer = null
        // Check if there are more orders to pay
        const sns = allOrderSns.value
        const idx = sns.indexOf(route.params.orderSn as string)
        if (idx >= 0 && idx < sns.length - 1) {
          setTimeout(() => router.push(`/pay/${sns[idx + 1]}?sns=${sns.join(',')}`), 1000)
        } else {
          allPaid.value = true
          setTimeout(() => router.push('/my-courses'), 1500)
        }
      }
    } catch {
      // ignore poll errors
    }
  }, 3000)
}

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.pay-box {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: flex-start;
}
.multi-badge {
  margin-bottom: 16px;
  padding: 8px 14px;
  background: var(--primary-fixed, #e8f4fd);
  color: var(--primary, #409eff);
  border-radius: var(--radius, 6px);
  font-size: 13px;
  font-weight: 600;
  display: inline-block;
}
.amount-row {
  margin-bottom: 16px;
  font-size: 16px;
}
.amount-label {
  color: #606266;
}
.amount-value {
  color: #f56c6c;
  font-size: 24px;
  font-weight: bold;
}
.error {
  color: #f56c6c;
}
.mock-hint {
  color: #909399;
  font-size: 14px;
}
.success-hint {
  color: #67c23a;
  font-size: 16px;
  font-weight: bold;
}
.qr-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.qr-tip {
  color: #909399;
  font-size: 14px;
}
.pay-hint {
  margin-top: 24px;
  color: #c0c4cc;
  font-size: 12px;
  text-align: center;
}
</style>
